import pytest
from pydantic import SecretStr
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from hikvision_downloader.core.auth import create_authenticated_session
from hikvision_downloader.core.models import NVRAuthCredentials


def test_create_authenticated_session_digest_auth() -> None:
    session = create_authenticated_session(
        host="192.168.1.100",
        port=80,
        username="admin",
        password="testpassword",
    )
    assert isinstance(session.auth, HTTPDigestAuth)
    assert session.auth.username == "admin"
    assert session.auth.password == "testpassword"
    assert "User-Agent" in session.headers


def test_create_authenticated_session_with_secret_str() -> None:
    secret = SecretStr("supersecret")
    session = create_authenticated_session(
        host="192.168.1.100",
        port=8000,
        username="admin",
        password=secret,
    )
    assert isinstance(session.auth, HTTPDigestAuth)
    assert session.auth.username == "admin"
    assert session.auth.password == "supersecret"
    # Ensure password is masked when converting SecretStr to string
    assert "supersecret" not in str(secret)


def test_create_authenticated_session_basic_auth() -> None:
    session = create_authenticated_session(
        host="192.168.1.100",
        username="admin",
        password="testpassword",
        auth_type="basic",
    )
    assert isinstance(session.auth, HTTPBasicAuth)
    assert session.auth.username == "admin"
    assert session.auth.password == "testpassword"


def test_create_authenticated_session_with_credentials_model() -> None:
    creds = NVRAuthCredentials(
        host="192.168.1.100",
        port=8080,
        username="operator",
        password=SecretStr("operatorpass"),
    )
    session = create_authenticated_session(credentials=creds)
    assert isinstance(session.auth, HTTPDigestAuth)
    assert session.auth.username == "operator"
    assert session.auth.password == "operatorpass"


def test_create_authenticated_session_missing_auth() -> None:
    with pytest.raises(RuntimeError, match="No valid authentication credentials provided"):
        create_authenticated_session()


def test_create_authenticated_session_custom_user_agent() -> None:
    session = create_authenticated_session(
        username="admin",
        password="secretpassword",
        user_agent="CustomCCTV/2.0",
    )
    assert session.headers.get("User-Agent") == "CustomCCTV/2.0"
    assert isinstance(session.auth, HTTPDigestAuth)
