"""Secure OS Keychain credential management for Hikvision Downloader."""

import logging

import keyring
import keyring.errors

logger = logging.getLogger(__name__)

KEYCHAIN_SERVICE: str = "hikvision_downloader"


def format_account_key(username: str, host: str, port: int = 80) -> str:
    """Format standard account key following the convention username@host:port."""
    return f"{username.strip()}@{host.strip()}:{port}"


def parse_account_key(account: str) -> tuple[str, str, int] | None:
    """Parse account key formatted as username@host:port or username@host (or legacy host:port:username).

    Returns:
        tuple of (username, host, port) or None if account format is invalid.
    """
    clean_account = account.strip()
    if not clean_account:
        return None

    # Standard format: username@host:port or username@host
    if "@" in clean_account:
        user_part, host_part = clean_account.split("@", 1)
        if ":" in host_part:
            host_str, port_str = host_part.split(":", 1)
            try:
                return user_part, host_str, int(port_str)
            except ValueError:
                return user_part, host_str, 80
        return user_part, host_part, 80

    # Legacy fallback format: host:port:username or host:username
    parts = clean_account.split(":")
    if len(parts) == 3:
        host, port_str, username = parts
        try:
            return username, host, int(port_str)
        except ValueError:
            return f"{port_str}:{username}", host, 80
    if len(parts) == 2:
        host, username = parts
        return username, host, 80

    return None


def save_nvr_password(host: str, username: str, password: str, port: int = 80) -> bool:
    """Persist NVR password securely in the OS keychain."""
    clean_host = host.strip()
    clean_user = username.strip()
    if not clean_host or not clean_user or not password:
        logger.debug("save_nvr_password called with empty host, username, or password")
        return False

    account = format_account_key(clean_user, clean_host, port)
    try:
        keyring.set_password(KEYCHAIN_SERVICE, account, password)
        logger.info("Successfully saved password in OS Keychain for account: %s", account)
        return True
    except (keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
        logger.warning("Failed to save password in OS Keychain for %s: %s", account, err)
        return False


def get_nvr_password(host: str, username: str, port: int = 80) -> str | None:
    """Retrieve NVR password securely from the OS keychain if present."""
    clean_host = host.strip()
    clean_user = username.strip()
    if not clean_host or not clean_user:
        logger.debug("get_nvr_password called with empty host or username")
        return None

    # 1. Primary standard query: username@host:port
    account = format_account_key(clean_user, clean_host, port)
    try:
        pw = keyring.get_password(KEYCHAIN_SERVICE, account)
        if pw is not None:
            logger.debug("OS Keychain query matched primary account: %s", account)
            return pw
    except (keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
        logger.warning("OS Keychain error while querying account %s: %s", account, err)

    # 2. Standard fallback query (default port 80): username@host
    if port != 80:
        fallback_std = format_account_key(clean_user, clean_host, 80)
        try:
            pw = keyring.get_password(KEYCHAIN_SERVICE, fallback_std)
            if pw is not None:
                logger.debug("OS Keychain query matched fallback account: %s", fallback_std)
                return pw
        except (keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
            logger.warning("OS Keychain error while querying account %s: %s", fallback_std, err)

    # 3. Legacy formats fallback
    for legacy in [f"{clean_host}:{port}:{clean_user}", f"{clean_host}:{clean_user}"]:
        try:
            pw = keyring.get_password(KEYCHAIN_SERVICE, legacy)
            if pw is not None:
                logger.debug("OS Keychain query matched legacy account: %s", legacy)
                return pw
        except (keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
            logger.warning("OS Keychain error while querying legacy account %s: %s", legacy, err)

    logger.debug("OS Keychain query for %s returned no entry", account)
    return None


def get_nvr_credential(host: str, username: str = "", port: int = 80) -> tuple[str, str] | None:
    """Retrieve stored NVR credential (username, password) from the OS keychain.

    Supports exact username matching or auto-discovery of stored credentials for host.
    """
    clean_host = host.strip()
    clean_user = username.strip()
    if not clean_host:
        logger.debug("get_nvr_credential called with empty host")
        return None

    # If specific username provided, try direct lookup first
    if clean_user:
        pw = get_nvr_password(clean_host, clean_user, port)
        if pw is not None:
            return clean_user, pw

    # Auto-discovery across stored credentials
    try:
        cred = keyring.get_credential(KEYCHAIN_SERVICE, None)
        if cred is not None and cred.username and cred.password:
            parsed = parse_account_key(cred.username)
            if parsed is not None:
                stored_user, stored_host, stored_port = parsed
                if stored_host.lower() == clean_host.lower() and (stored_port == port or stored_port == 80 or port == 80):
                    logger.debug("OS Keychain discovered stored credential for %s: user=%s", clean_host, stored_user)
                    return stored_user, cred.password
    except (keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
        logger.warning("OS Keychain error during generic credential discovery: %s", err)

    # Secondary discovery via saved usernames in QSettings
    try:
        from .settings import get_saved_usernames_from_settings

        saved_users = get_saved_usernames_from_settings(clean_host)
        for u in saved_users:
            if u != clean_user:
                pw = get_nvr_password(clean_host, u, port)
                if pw is not None:
                    return u, pw
    except (OSError, RuntimeError, ValueError) as err:
        logger.warning("Error during QSettings username traversal for keychain: %s", err)

    query_repr = f"{clean_user}@{clean_host}:{port}" if clean_user else f"@{clean_host}:{port}"
    logger.debug("OS Keychain query for %s returned no entry", query_repr)
    return None


def delete_nvr_password(host: str, username: str, port: int = 80) -> bool:
    """Remove stored NVR password from the OS keychain."""
    clean_host = host.strip()
    clean_user = username.strip()
    if not clean_host or not clean_user:
        logger.debug("delete_nvr_password called with empty host or username")
        return False

    account = format_account_key(clean_user, clean_host, port)
    deleted = False

    try:
        keyring.delete_password(KEYCHAIN_SERVICE, account)
        logger.info("Deleted OS Keychain password for %s", account)
        deleted = True
    except (keyring.errors.PasswordDeleteError, keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
        logger.debug("Primary account %s could not be deleted from keychain: %s", account, err)

    # Also remove variations & legacy formats
    for alt_key in [
        format_account_key(clean_user, clean_host, 80),
        f"{clean_host}:{port}:{clean_user}",
        f"{clean_host}:{clean_user}",
    ]:
        if alt_key != account:
            try:
                keyring.delete_password(KEYCHAIN_SERVICE, alt_key)
                logger.debug("Deleted alternate keychain entry %s", alt_key)
                deleted = True
            except (keyring.errors.PasswordDeleteError, keyring.errors.KeyringError, OSError, RuntimeError, ValueError):
                pass

    return deleted
