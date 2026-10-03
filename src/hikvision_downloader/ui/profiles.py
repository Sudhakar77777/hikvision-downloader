"""Storage helper and data structures for saved NVR connection profiles."""

import json
import logging
import time
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)

PROFILES_DIR: Path = Path.home() / ".hikvision-downloader"
PROFILES_FILE: Path = PROFILES_DIR / "profiles.json"


class NvrProfile(BaseModel):
    """Saved NVR connection endpoint configuration."""

    host: str = Field(min_length=1, description="NVR Host IP or domain name")
    port: int = Field(default=80, ge=1, le=65535, description="NVR HTTP/ISAPI port")
    username: str = Field(default="admin", min_length=1, description="NVR Login username")
    last_used: float = Field(default_factory=time.time, description="Epoch timestamp of last successful connection")

    @model_validator(mode="after")
    def clean_fields(self) -> Self:
        self.host = self.host.strip()
        self.username = self.username.strip()
        return self


def get_profiles_path(custom_path: Path | None = None) -> Path:
    """Resolve the storage path for profiles JSON file."""
    return custom_path if custom_path is not None else PROFILES_FILE


def load_profiles(file_path: Path | None = None) -> list[NvrProfile]:
    """Load saved NVR profiles from disk, ordered by most recently used."""
    path = get_profiles_path(file_path)
    if not path.exists():
        logger.debug("Profiles file does not exist at: %s", path)
        return []

    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        raw_list = json.loads(content)
        if not isinstance(raw_list, list):
            logger.warning("Corrupted profiles file at %s: root is not a list", path)
            return []

        profiles: list[NvrProfile] = []
        for item in raw_list:
            if isinstance(item, dict):
                try:
                    profiles.append(NvrProfile.model_validate(item))
                except (ValueError, TypeError) as val_err:
                    logger.warning("Skipping invalid profile entry in %s: %s", path, val_err)

        profiles.sort(key=lambda p: p.last_used, reverse=True)
        return profiles
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as err:
        logger.warning("Failed to read NVR profiles from %s: %s", path, err)
        return []


def save_profile(
    host: str,
    port: int = 80,
    username: str = "admin",
    file_path: Path | None = None,
) -> bool:
    """Save or update an NVR profile to disk."""
    clean_host = host.strip()
    clean_user = username.strip()
    if not clean_host or not clean_user:
        logger.debug("save_profile called with empty host or username")
        return False

    path = get_profiles_path(file_path)
    try:
        profiles = load_profiles(file_path=path)
        # Filter out existing matching (host, port, username)
        filtered = [
            p for p in profiles
            if not (p.host.lower() == clean_host.lower() and p.port == port and p.username == clean_user)
        ]
        # Insert current profile at head
        new_profile = NvrProfile(
            host=clean_host,
            port=port,
            username=clean_user,
            last_used=time.time(),
        )
        filtered.insert(0, new_profile)

        # Cap stored history to 50 profiles
        final_list = filtered[:50]

        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps([p.model_dump() for p in final_list], indent=2)
        path.write_text(serialized, encoding="utf-8")
        logger.debug("Saved NVR profile for %s@%s:%d to %s", clean_user, clean_host, port, path)
        return True
    except (OSError, ValueError, TypeError) as err:
        logger.warning("Failed to save NVR profile for %s@%s:%d to %s: %s", clean_user, clean_host, port, path, err)
        return False


def delete_profile(
    host: str,
    port: int = 80,
    username: str = "admin",
    file_path: Path | None = None,
) -> bool:
    """Remove a saved NVR profile from disk."""
    clean_host = host.strip()
    clean_user = username.strip()
    if not clean_host:
        return False

    path = get_profiles_path(file_path)
    if not path.exists():
        return False

    try:
        profiles = load_profiles(file_path=path)
        initial_len = len(profiles)
        filtered = [
            p for p in profiles
            if not (p.host.lower() == clean_host.lower() and p.port == port and p.username == clean_user)
        ]
        if len(filtered) == initial_len:
            return False

        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps([p.model_dump() for p in filtered], indent=2)
        path.write_text(serialized, encoding="utf-8")
        logger.debug("Deleted NVR profile for %s@%s:%d from %s", clean_user, clean_host, port, path)
        return True
    except (OSError, ValueError) as err:
        logger.warning("Failed to delete NVR profile from %s: %s", path, err)
        return False


def get_saved_hosts(file_path: Path | None = None) -> list[str]:
    """Return unique list of saved hosts in MRU order."""
    profiles = load_profiles(file_path)
    seen: set[str] = set()
    hosts: list[str] = []
    for p in profiles:
        if p.host not in seen:
            seen.add(p.host)
            hosts.append(p.host)
    return hosts


def get_saved_usernames(host: str | None = None, file_path: Path | None = None) -> list[str]:
    """Return unique list of saved usernames (optionally filtered by host) in MRU order."""
    profiles = load_profiles(file_path)
    clean_host = host.strip().lower() if host else None
    seen: set[str] = set()
    users: list[str] = []
    for p in profiles:
        if (clean_host is None or p.host.lower() == clean_host) and p.username not in seen:
            seen.add(p.username)
            users.append(p.username)
    return users
