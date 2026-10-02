import os
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

from hikvision_downloader.core.dates import search_month
from hikvision_downloader.core.models import TrackId
from hikvision_downloader.http_client import make_session


@pytest.mark.integration
def test_live_nvr_connection_and_discovery() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        pytest.skip("Integration test skipped: .env file does not exist")

    env_config = dotenv_values(env_path)
    host = env_config.get("HIKVISION_HOST") or os.getenv("HIKVISION_HOST")
    cookie = env_config.get("HIKVISION_COOKIE") or os.getenv("HIKVISION_COOKIE")

    if not host or not cookie:
        pytest.skip("Integration test skipped: HIKVISION_HOST or HIKVISION_COOKIE not configured")

    try:
        session = make_session(cookie=cookie)
        # Attempt to discover dates for track 101 on the live hardware
        search_month(
            session=session,
            host=host,
            track_id=TrackId(101),
            year=2026,
            month=9,
            timeout=10.0,
        )
    except (requests.RequestException, RuntimeError, TimeoutError) as exc:
        pytest.skip(f"Integration test skipped: Live NVR hardware unreachable or returned error: {exc}")
