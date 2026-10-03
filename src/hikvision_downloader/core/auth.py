import requests
from pydantic import SecretStr
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from ..config import USER_AGENT
from .models import NVRAuthCredentials


def create_authenticated_session(
    host: str | None = None,
    port: int = 80,
    username: str | None = None,
    password: str | SecretStr | None = None,
    user_agent: str | None = None,
    credentials: NVRAuthCredentials | None = None,
    auth_type: str = "digest",
) -> requests.Session:
    """Create an authenticated HTTP requests.Session using Digest auth or Basic auth.

    Passwords are treated as sensitive secrets via SecretStr and are never logged or exposed.
    """
    effective_username = credentials.username if credentials is not None else username
    effective_password = credentials.password if credentials is not None else password

    if not effective_username or not effective_password:
        raise RuntimeError("No valid authentication credentials provided (username and password required).")

    session = requests.Session()
    agent = user_agent or USER_AGENT
    session.headers["User-Agent"] = agent

    raw_password = effective_password.get_secret_value() if isinstance(effective_password, SecretStr) else str(effective_password)

    if auth_type.lower() == "basic":
        session.auth = HTTPBasicAuth(effective_username, raw_password)
    else:
        session.auth = HTTPDigestAuth(effective_username, raw_password)

    return session
