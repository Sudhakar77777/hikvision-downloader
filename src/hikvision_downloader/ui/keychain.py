"""Secure OS Keychain credential management for Hikvision Downloader."""

import logging

import keyring
import keyring.errors

logger = logging.getLogger(__name__)

KEYCHAIN_SERVICE: str = "hikvision_downloader"


def parse_account_key(account: str) -> tuple[str, int | None, str] | None:
    """Parse account key formatted as host:port:username or host:username.

    Returns:
        tuple of (host, port, username) or None if account format is invalid.
    """
    clean_account = account.strip()
    if not clean_account:
        return None
    parts = clean_account.split(":")
    if len(parts) == 3:
        host, port_str, username = parts
        try:
            return host, int(port_str), username
        except ValueError:
            return host, None, f"{port_str}:{username}"
    if len(parts) == 2:
        host, username = parts
        return host, None, username
    return None


def _primary_account_key(host: str, username: str, port: int = 80) -> str:
    """Format primary account key (host:port:username)."""
    return f"{host.strip()}:{port}:{username.strip()}"


def _fallback_account_key(host: str, username: str) -> str:
    """Format fallback account key (host:username)."""
    return f"{host.strip()}:{username.strip()}"


def save_nvr_password(host: str, username: str, password: str, port: int = 80) -> bool:
    """Persist NVR password securely in the OS keychain."""
    if not host or not username or not password:
        logger.debug("save_nvr_password called with empty host, username, or password")
        return False

    account = _primary_account_key(host, username, port)
    try:
        keyring.set_password(KEYCHAIN_SERVICE, account, password)
        logger.debug("Successfully saved password in keychain for account: %s", account)
        return True
    except (keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
        logger.warning("Failed to save password in keychain for %s: %s", account, err)
        return False


def get_nvr_credential(host: str, username: str = "", port: int = 80) -> tuple[str, str] | None:
    """Retrieve stored NVR credential (username, password) from the OS keychain.

    Supports exact username matching or auto-discovery of stored credentials for host.
    """
    if not host:
        logger.debug("get_nvr_credential called with empty host")
        return None

    clean_host = host.strip()
    clean_user = username.strip()

    if clean_user:
        primary_account = _primary_account_key(clean_host, clean_user, port)
        try:
            pw = keyring.get_password(KEYCHAIN_SERVICE, primary_account)
            if pw is not None:
                logger.debug("Keychain query matched primary account: %s", primary_account)
                return clean_user, pw
        except (keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
            logger.warning("Keychain error while querying primary account %s: %s", primary_account, err)

        fallback_account = _fallback_account_key(clean_host, clean_user)
        try:
            pw = keyring.get_password(KEYCHAIN_SERVICE, fallback_account)
            if pw is not None:
                logger.debug("Keychain query matched fallback account: %s", fallback_account)
                return clean_user, pw
        except (keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
            logger.warning("Keychain error while querying fallback account %s: %s", fallback_account, err)

    # If username not provided or specific match missed, discover credentials stored for this service/host
    try:
        cred = keyring.get_credential(KEYCHAIN_SERVICE, None)
        if cred is not None and cred.username and cred.password:
            parsed = parse_account_key(cred.username)
            if parsed is not None:
                stored_host, stored_port, stored_user = parsed
                if stored_host == clean_host and (stored_port is None or stored_port == port or stored_port == 80 or port == 80):
                    logger.debug("Keychain discovered stored credential for %s: user=%s", clean_host, stored_user)
                    return stored_user, cred.password
    except (keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
        logger.warning("Keychain error during generic credential discovery: %s", err)

    query_repr = f"{clean_host}:{port}:{clean_user}" if clean_user else clean_host
    logger.debug("Keychain query for %s returned no entry", query_repr)
    return None


def get_nvr_password(host: str, username: str, port: int = 80) -> str | None:
    """Retrieve NVR password securely from the OS keychain if present."""
    if not host or not username:
        logger.debug("get_nvr_password called with empty host or username")
        return None

    clean_host = host.strip()
    clean_user = username.strip()
    primary_account = _primary_account_key(clean_host, clean_user, port)
    try:
        pw = keyring.get_password(KEYCHAIN_SERVICE, primary_account)
        if pw is not None:
            logger.debug("Keychain query matched primary account: %s", primary_account)
            return pw
    except (keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
        logger.warning("Keychain error while querying primary account %s: %s", primary_account, err)

    fallback_account = _fallback_account_key(clean_host, clean_user)
    try:
        pw = keyring.get_password(KEYCHAIN_SERVICE, fallback_account)
        if pw is not None:
            logger.debug("Keychain query matched fallback account: %s", fallback_account)
            return pw
    except (keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
        logger.warning("Keychain error while querying fallback account %s: %s", fallback_account, err)

    logger.debug("Keychain query for %s returned no entry", primary_account)
    return None


def delete_nvr_password(host: str, username: str, port: int = 80) -> bool:
    """Remove stored NVR password from the OS keychain."""
    if not host or not username:
        logger.debug("delete_nvr_password called with empty host or username")
        return False

    clean_host = host.strip()
    clean_user = username.strip()
    primary_account = _primary_account_key(clean_host, clean_user, port)
    fallback_account = _fallback_account_key(clean_host, clean_user)
    deleted = False

    try:
        keyring.delete_password(KEYCHAIN_SERVICE, primary_account)
        logger.debug("Deleted keychain password for %s", primary_account)
        deleted = True
    except (keyring.errors.PasswordDeleteError, keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
        logger.debug("Primary account %s could not be deleted from keychain: %s", primary_account, err)

    try:
        keyring.delete_password(KEYCHAIN_SERVICE, fallback_account)
        logger.debug("Deleted fallback keychain password for %s", fallback_account)
        deleted = True
    except (keyring.errors.PasswordDeleteError, keyring.errors.KeyringError, OSError, RuntimeError, ValueError) as err:
        logger.debug("Fallback account %s could not be deleted from keychain: %s", fallback_account, err)

    return deleted
