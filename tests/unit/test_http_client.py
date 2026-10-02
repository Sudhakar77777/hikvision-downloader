from unittest.mock import MagicMock

import pytest
import requests

from hikvision_downloader.http_client import make_session, request_with_retry


def test_make_session() -> None:
    session = make_session(user_agent="CustomAgent/1.0")
    assert session.headers.get("User-Agent") == "CustomAgent/1.0"


def test_request_with_retry_401_fails_immediately_without_retrying() -> None:
    """Verify that when 401 Unauthorized is returned, request_with_retry fails on first attempt with NO retries."""
    session = MagicMock(spec=requests.Session)
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    session.request.return_value = mock_resp

    with pytest.raises(RuntimeError, match="401 Unauthorized"):
        request_with_retry(session, "GET", "http://192.168.1.5/ISAPI/test", max_retries=3, retry_wait=0.01)

    # CRITICAL: Must be called EXACTLY ONCE to avoid triggering NVR security lockouts
    assert session.request.call_count == 1


def test_request_with_retry_403_fails_immediately_without_retrying() -> None:
    """Verify that when 403 Forbidden is returned, request_with_retry fails on first attempt with NO retries."""
    session = MagicMock(spec=requests.Session)
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 403
    mock_resp.text = "Forbidden"
    session.request.return_value = mock_resp

    with pytest.raises(RuntimeError, match="403 Forbidden"):
        request_with_retry(session, "GET", "http://192.168.1.5/ISAPI/test", max_retries=3, retry_wait=0.01)

    assert session.request.call_count == 1


def test_request_with_retry_transient_error_retries_and_recovers() -> None:
    """Verify that transient connection/500 errors are safely retried and recover."""
    session = MagicMock(spec=requests.Session)
    resp_fail = MagicMock(spec=requests.Response)
    resp_fail.status_code = 500
    resp_fail.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

    resp_ok = MagicMock(spec=requests.Response)
    resp_ok.status_code = 200
    resp_ok.raise_for_status.return_value = None

    session.request.side_effect = [resp_fail, resp_ok]

    resp = request_with_retry(session, "GET", "http://192.168.1.5/ISAPI/test", max_retries=3, retry_wait=0.01)
    assert resp.status_code == 200
    assert session.request.call_count == 2
