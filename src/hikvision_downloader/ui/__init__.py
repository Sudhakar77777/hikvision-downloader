"""PySide6 Native Desktop User Interface package for Hikvision Downloader."""

from .keychain import (
    delete_nvr_password,
    get_nvr_credential,
    get_nvr_password,
    parse_account_key,
    save_nvr_password,
)
from .profiles import (
    NvrProfile,
    delete_profile,
    get_saved_hosts,
    get_saved_usernames,
    load_profiles,
    save_profile,
)

__all__ = [
    "NvrProfile",
    "delete_nvr_password",
    "delete_profile",
    "get_nvr_credential",
    "get_nvr_password",
    "get_saved_hosts",
    "get_saved_usernames",
    "load_profiles",
    "parse_account_key",
    "save_nvr_password",
    "save_profile",
]
