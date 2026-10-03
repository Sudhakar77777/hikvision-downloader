"""PySide6 Native Desktop User Interface package for Hikvision Downloader."""

from .keychain import (
    delete_nvr_password,
    get_nvr_credential,
    get_nvr_password,
    parse_account_key,
    save_nvr_password,
)
from .settings import (
    ProfileMetadata,
    delete_profile_from_settings,
    get_saved_hosts_from_settings,
    get_saved_usernames_from_settings,
    get_settings,
    load_profiles_from_settings,
    restore_window_geometry,
    save_profile_to_settings,
    save_window_geometry,
)

__all__ = [
    "ProfileMetadata",
    "delete_nvr_password",
    "delete_profile_from_settings",
    "get_nvr_credential",
    "get_nvr_password",
    "get_saved_hosts_from_settings",
    "get_saved_usernames_from_settings",
    "get_settings",
    "load_profiles_from_settings",
    "parse_account_key",
    "restore_window_geometry",
    "save_nvr_password",
    "save_profile_to_settings",
    "save_window_geometry",
]

