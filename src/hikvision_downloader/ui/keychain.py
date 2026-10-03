"""Secure OS Keychain credential management for Hikvision Downloader."""

import keyring
import keyring.errors

KEYCHAIN_SERVICE: str = "hikvision_downloader"


def _account_key(host: str, username: str, port: int = 80) -> str:
    """Format account key for OS keychain lookup."""
    clean_host = host.strip()
    clean_user = username.strip()
    if port and port != 80 and ":" not in clean_host:
        return f"{clean_host}:{port}:{clean_user}"
    return f"{clean_host}:{clean_user}"


def save_nvr_password(host: str, username: str, password: str, port: int = 80) -> bool:
    """Persist NVR password securely in the OS keychain."""
    if not host or not username or not password:
        return False

    account = _account_key(host, username, port)
    try:
        keyring.set_password(KEYCHAIN_SERVICE, account, password)
        return True
    except keyring.errors.KeyringError, OSError, RuntimeError, ValueError:
        return False


def get_nvr_password(host: str, username: str, port: int = 80) -> str | None:
    """Retrieve NVR password securely from the OS keychain if present."""
    if not host or not username:
        return None

    primary_account = _account_key(host, username, port)
    try:
        pw = keyring.get_password(KEYCHAIN_SERVICE, primary_account)
        if pw is not None:
            return pw

        # Fallback to plain host:username if port-specific entry is missing
        if port and port != 80:
            fallback_account = f"{host.strip()}:{username.strip()}"
            return keyring.get_password(KEYCHAIN_SERVICE, fallback_account)
        return None
    except keyring.errors.KeyringError, OSError, RuntimeError, ValueError:
        return None


def delete_nvr_password(host: str, username: str, port: int = 80) -> bool:
    """Remove stored NVR password from the OS keychain."""
    if not host or not username:
        return False

    account = _account_key(host, username, port)
    try:
        keyring.delete_password(KEYCHAIN_SERVICE, account)
        return True
    except keyring.errors.KeyringError, OSError, RuntimeError, ValueError:
        return False
