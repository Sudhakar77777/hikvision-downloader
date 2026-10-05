"""Native cross-platform application settings and profile metadata persistence using QSettings."""

import json
import logging
import time
from typing import Self

from pydantic import BaseModel, Field, model_validator
from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

ORGANIZATION_NAME: str = "Arivedha"
APPLICATION_NAME: str = "HikVisionDownloader"


class ProfileMetadata(BaseModel):
    """Saved NVR connection endpoint metadata (strictly non-sensitive, zero passwords)."""

    host: str = Field(min_length=1, description="NVR Host IP or domain name")
    port: int = Field(default=80, ge=1, le=65535, description="NVR HTTP/ISAPI port")
    username: str = Field(default="admin", min_length=1, description="NVR Login username")
    last_used: float = Field(default_factory=time.time, description="Epoch timestamp of last successful connection")

    @model_validator(mode="after")
    def clean_fields(self) -> Self:
        self.host = self.host.strip()
        self.username = self.username.strip()
        return self


def get_settings(custom_settings: QSettings | None = None) -> QSettings:
    """Return configured QSettings instance for Arivedha / HikVisionDownloader."""
    if custom_settings is not None:
        return custom_settings
    return QSettings(ORGANIZATION_NAME, APPLICATION_NAME)


def load_profiles_from_settings(settings: QSettings | None = None) -> list[ProfileMetadata]:
    """Load saved NVR connection profiles metadata from QSettings in MRU order."""
    s = get_settings(settings)
    raw_val = s.value("profiles_metadata", "[]")

    if not isinstance(raw_val, str):
        if isinstance(raw_val, QByteArray):
            raw_val = bytes(raw_val.data()).decode("utf-8")
        elif isinstance(raw_val, (bytes, bytearray)):
            raw_val = raw_val.decode("utf-8")
        else:
            raw_val = str(raw_val)

    if not raw_val or raw_val == "[]":
        return []

    try:
        data = json.loads(raw_val)
        if not isinstance(data, list):
            logger.warning("Corrupted profiles_metadata in QSettings: expected list")
            return []

        profiles: list[ProfileMetadata] = []
        for item in data:
            if isinstance(item, dict):
                try:
                    profiles.append(ProfileMetadata.model_validate(item))
                except (ValueError, TypeError) as err:
                    logger.warning("Skipping invalid profile entry in QSettings: %s", err)

        profiles.sort(key=lambda p: p.last_used, reverse=True)
        return profiles
    except (json.JSONDecodeError, UnicodeDecodeError) as err:
        logger.warning("Failed to parse profiles_metadata from QSettings: %s", err)
        return []


def save_profile_to_settings(
    host: str,
    port: int = 80,
    username: str = "admin",
    settings: QSettings | None = None,
) -> bool:
    """Save or update NVR profile metadata in QSettings."""
    clean_host = host.strip()
    clean_user = username.strip()
    if not clean_host or not clean_user:
        logger.debug("save_profile_to_settings called with empty host or username")
        return False

    s = get_settings(settings)
    try:
        profiles = load_profiles_from_settings(s)
        # Filter out existing matching (host, port, username)
        filtered = [p for p in profiles if not (p.host.lower() == clean_host.lower() and p.port == port and p.username == clean_user)]
        # Insert current profile at head
        new_profile = ProfileMetadata(
            host=clean_host,
            port=port,
            username=clean_user,
            last_used=time.time(),
        )
        filtered.insert(0, new_profile)

        # Cap stored history to 50 profiles
        final_list = filtered[:50]
        serialized = json.dumps([p.model_dump() for p in final_list])
        s.setValue("profiles_metadata", serialized)

        # Also store top-level recent hosts and usernames
        hosts = get_saved_hosts_from_settings(s)
        s.setValue("recent_hosts", hosts)

        logger.debug("Saved NVR profile metadata for %s@%s:%d in QSettings", clean_user, clean_host, port)
        return True
    except (ValueError, TypeError, OSError) as err:
        logger.warning("Failed to save NVR profile metadata for %s@%s:%d in QSettings: %s", clean_user, clean_host, port, err)
        return False


def delete_profile_from_settings(
    host: str,
    port: int = 80,
    username: str = "admin",
    settings: QSettings | None = None,
) -> bool:
    """Remove a saved NVR profile entry from QSettings."""
    clean_host = host.strip()
    clean_user = username.strip()
    if not clean_host:
        return False

    s = get_settings(settings)
    try:
        profiles = load_profiles_from_settings(s)
        initial_len = len(profiles)
        filtered = [
            p
            for p in profiles
            if not (
                p.host.lower() == clean_host.lower()
                and (port is None or p.port == port or port == 80)
                and (not clean_user or p.username.lower() == clean_user.lower())
            )
        ]
        if len(filtered) == initial_len:
            return False

        serialized = json.dumps([p.model_dump() for p in filtered])
        s.setValue("profiles_metadata", serialized)

        # Update recent hosts
        hosts = [p.host for p in filtered]
        seen_hosts: set[str] = set()
        unique_hosts: list[str] = []
        for h in hosts:
            if h not in seen_hosts:
                seen_hosts.add(h)
                unique_hosts.append(h)
        s.setValue("recent_hosts", unique_hosts)

        logger.debug("Deleted NVR profile metadata for %s@%s:%d from QSettings", clean_user, clean_host, port)
        return True
    except (ValueError, OSError) as err:
        logger.warning("Failed to delete NVR profile metadata from QSettings: %s", err)
        return False


def get_saved_hosts_from_settings(settings: QSettings | None = None) -> list[str]:
    """Return unique list of saved hosts in MRU order from QSettings."""
    profiles = load_profiles_from_settings(settings)
    seen: set[str] = set()
    hosts: list[str] = []
    for p in profiles:
        if p.host not in seen:
            seen.add(p.host)
            hosts.append(p.host)
    return hosts


def get_saved_usernames_from_settings(host: str | None = None, settings: QSettings | None = None) -> list[str]:
    """Return unique list of saved usernames (optionally filtered by host) in MRU order from QSettings."""
    profiles = load_profiles_from_settings(settings)
    clean_host = host.strip().lower() if host else None
    seen: set[str] = set()
    users: list[str] = []
    for p in profiles:
        if (clean_host is None or p.host.lower() == clean_host) and p.username not in seen:
            seen.add(p.username)
            users.append(p.username)
    return users


def save_window_geometry(window: QWidget, settings: QSettings | None = None) -> None:
    """Save window geometry and state to QSettings."""
    s = get_settings(settings)
    s.setValue("window_geometry", window.saveGeometry())


def restore_window_geometry(window: QWidget, settings: QSettings | None = None) -> bool:
    """Restore window geometry and state from QSettings if available."""
    s = get_settings(settings)
    geom = s.value("window_geometry")
    if geom is not None and isinstance(geom, (QByteArray, bytes)):
        return window.restoreGeometry(QByteArray(geom) if isinstance(geom, bytes) else geom)
    return False
