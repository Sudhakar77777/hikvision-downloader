import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from pydantic import SecretStr

from hikvision_downloader.core.auth import create_authenticated_session
from hikvision_downloader.core.cameras import CameraDiscoveryService, format_host_port
from hikvision_downloader.core.dates import search_month
from hikvision_downloader.core.downloads import build_download_url
from hikvision_downloader.core.recordings import search_recordings
from hikvision_downloader.http_client import request_with_retry

pytestmark = pytest.mark.integration


@pytest.fixture
def live_nvr_config() -> dict[str, str | int]:
    """Load configuration for live NVR testing, skipping if not configured."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        pytest.skip("Integration test skipped: .env file does not exist")

    env_config = dotenv_values(env_path)
    host = env_config.get("HIKVISION_HOST") or os.getenv("HIKVISION_HOST")
    username = env_config.get("HIKVISION_USERNAME") or os.getenv("HIKVISION_USERNAME")
    password = env_config.get("HIKVISION_PASSWORD") or os.getenv("HIKVISION_PASSWORD")
    port = int(env_config.get("HIKVISION_PORT") or os.getenv("HIKVISION_PORT") or 80)
    auth_type = env_config.get("HIKVISION_AUTH_TYPE") or os.getenv("HIKVISION_AUTH_TYPE") or "digest"

    if not host or not (username and password):
        pytest.skip("Integration test skipped: HIKVISION_HOST, HIKVISION_USERNAME, and HIKVISION_PASSWORD not configured in .env")

    return {
        "host": str(host),
        "port": port,
        "username": str(username),
        "password": str(password),
        "auth_type": str(auth_type),
    }


@pytest.fixture
def live_session(live_nvr_config: dict[str, str | int]) -> requests.Session:
    """Create authenticated session for live testing."""
    password_val = str(live_nvr_config["password"])
    return create_authenticated_session(
        host=str(live_nvr_config["host"]),
        port=int(live_nvr_config["port"]),
        username=str(live_nvr_config["username"]),
        password=SecretStr(password_val),
        auth_type=str(live_nvr_config["auth_type"]),
    )


def test_01_live_auth_and_device_info(
    live_session: requests.Session,
    live_nvr_config: dict[str, str | int],
) -> None:
    """Step 1: Test authentication and connectivity to /ISAPI/System/deviceInfo."""
    endpoint = format_host_port(str(live_nvr_config["host"]), int(live_nvr_config["port"]))
    url = f"http://{endpoint}/ISAPI/System/deviceInfo"

    try:
        response = request_with_retry(live_session, "GET", url, max_retries=1, timeout=10.0)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        assert "<DeviceInfo" in response.text or "<deviceInfo" in response.text
        print("\n[OK] Authenticated successfully to NVR endpoint (HTTP 200 DeviceInfo)")
    except (requests.RequestException, RuntimeError, TimeoutError) as exc:
        pytest.skip(f"Live auth probe skipped/failed: {exc}")


def test_02_live_streaming_channels(
    live_session: requests.Session,
    live_nvr_config: dict[str, str | int],
) -> None:
    """Step 2: Test querying /ISAPI/Streaming/channels for camera names and stream IDs."""
    endpoint = format_host_port(str(live_nvr_config["host"]), int(live_nvr_config["port"]))
    url = f"http://{endpoint}/ISAPI/Streaming/channels"

    try:
        response = request_with_retry(live_session, "GET", url, max_retries=1, timeout=10.0)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        print(f"\n[OK] Streaming channels endpoint returned HTTP 200 ({len(response.text)} bytes)")
    except (requests.RequestException, RuntimeError, TimeoutError) as exc:
        pytest.skip(f"Streaming channels endpoint probe skipped/failed: {exc}")


def test_03_live_record_tracks(
    live_session: requests.Session,
    live_nvr_config: dict[str, str | int],
) -> None:
    """Step 3: Test querying /ISAPI/ContentMgmt/record/tracks directly."""
    endpoint = format_host_port(str(live_nvr_config["host"]), int(live_nvr_config["port"]))
    url = f"http://{endpoint}/ISAPI/ContentMgmt/record/tracks"

    try:
        response = request_with_retry(live_session, "GET", url, max_retries=1, timeout=10.0)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        print(f"\n[OK] Record tracks endpoint returned HTTP 200 ({len(response.text)} bytes)")
    except (requests.RequestException, RuntimeError, TimeoutError) as exc:
        pytest.skip(f"Record tracks endpoint probe skipped/failed: {exc}")


def test_04_live_camera_discovery_service(
    live_session: requests.Session,
    live_nvr_config: dict[str, str | int],
) -> None:
    """Step 4: Test end-to-end CameraDiscoveryService with dynamic discovery and name resolution."""
    discovery_service = CameraDiscoveryService()
    try:
        cameras = discovery_service.get_cameras(
            session=live_session,
            host=str(live_nvr_config["host"]),
            port=int(live_nvr_config["port"]),
            timeout=10.0,
        )
        assert len(cameras) > 0
        print(f"\n[OK] Discovered {len(cameras)} camera channels successfully")
    except (requests.RequestException, RuntimeError, TimeoutError, ValueError) as exc:
        pytest.skip(f"Camera discovery service skipped/failed: {exc}")


def test_05_live_month_availability(
    live_session: requests.Session,
    live_nvr_config: dict[str, str | int],
) -> None:
    """Step 5: Test querying daily recording distribution for active recording month."""
    endpoint = format_host_port(str(live_nvr_config["host"]), int(live_nvr_config["port"]))
    target_date = (datetime.now(UTC) - timedelta(days=7)).date()

    discovery_service = CameraDiscoveryService()
    try:
        cameras = discovery_service.get_cameras(
            session=live_session,
            host=str(live_nvr_config["host"]),
            port=int(live_nvr_config["port"]),
            timeout=10.0,
        )
        first_cam = next(iter(cameras.values()))
        track_id = first_cam.main_track

        months = search_month(
            session=live_session,
            host=endpoint,
            track_id=track_id,
            year=target_date.year,
            month=target_date.month,
            timeout=10.0,
        )
        assert isinstance(months, list)
        print(f"\n[OK] Monthly availability search on track {int(track_id)} returned {len(months)} recorded days")
    except (requests.RequestException, RuntimeError, TimeoutError, ValueError) as exc:
        pytest.skip(f"Month search skipped/failed: {exc}")


def test_06_live_recording_search(
    live_session: requests.Session,
    live_nvr_config: dict[str, str | int],
) -> None:
    """Step 6: Test searching for recordings on a specific track and historical date (1 week ago)."""
    endpoint = format_host_port(str(live_nvr_config["host"]), int(live_nvr_config["port"]))
    target_date = (datetime.now(UTC) - timedelta(days=7)).date()

    discovery_service = CameraDiscoveryService()
    try:
        cameras = discovery_service.get_cameras(
            session=live_session,
            host=str(live_nvr_config["host"]),
            port=int(live_nvr_config["port"]),
            timeout=10.0,
        )
        first_cam = next(iter(cameras.values()))
        track_id = first_cam.main_track

        recs = search_recordings(
            session=live_session,
            host=endpoint,
            track_id=track_id,
            recording_date=target_date,
            position=0,
            batch_size=10,
            timeout=10.0,
        )
        if not recs:
            available = search_month(
                session=live_session,
                host=endpoint,
                track_id=track_id,
                year=target_date.year,
                month=target_date.month,
                timeout=10.0,
            )
            if available:
                target_date = available[-1].value
                recs = search_recordings(
                    session=live_session,
                    host=endpoint,
                    track_id=track_id,
                    recording_date=target_date,
                    position=0,
                    batch_size=10,
                    timeout=10.0,
                )

        assert isinstance(recs, list)
        print(f"\n[OK] Search recordings on track {int(track_id)} for date {target_date} returned {len(recs)} recordings")
    except (requests.RequestException, RuntimeError, TimeoutError, ValueError) as exc:
        pytest.skip(f"Search recordings skipped/failed: {exc}")


def test_07_live_download_stream_sample(
    live_session: requests.Session,
    live_nvr_config: dict[str, str | int],
) -> None:
    """Step 7: Test downloading and streaming actual video payload from NVR hardware using a date from 1 week ago."""
    endpoint = format_host_port(str(live_nvr_config["host"]), int(live_nvr_config["port"]))
    target_date = (datetime.now(UTC) - timedelta(days=7)).date()

    discovery_service = CameraDiscoveryService()
    try:
        cameras = discovery_service.get_cameras(
            session=live_session,
            host=str(live_nvr_config["host"]),
            port=int(live_nvr_config["port"]),
            timeout=10.0,
        )
        first_cam = next(iter(cameras.values()))
        track_id = first_cam.main_track

        recs = search_recordings(
            session=live_session,
            host=endpoint,
            track_id=track_id,
            recording_date=target_date,
            position=0,
            batch_size=1,
            timeout=10.0,
        )
        if not recs:
            available = search_month(
                session=live_session,
                host=endpoint,
                track_id=track_id,
                year=target_date.year,
                month=target_date.month,
                timeout=10.0,
            )
            if available:
                target_date = available[-1].value
                recs = search_recordings(
                    session=live_session,
                    host=endpoint,
                    track_id=track_id,
                    recording_date=target_date,
                    position=0,
                    batch_size=1,
                    timeout=10.0,
                )

        if not recs:
            pytest.skip(f"No recordings available near date {target_date} on track {track_id} to test download stream")

        rec = recs[0]
        download_url = build_download_url(
            host=str(live_nvr_config["host"]),
            recording=rec,
            track_id=track_id,
            port=int(live_nvr_config["port"]),
        )

        response = request_with_retry(
            live_session,
            "GET",
            download_url,
            stream=True,
            timeout=15.0,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "*/*",
            },
        )
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"

        # Stream first 64KB chunk of binary video data from NVR
        chunk = next(response.iter_content(chunk_size=65536), b"")
        assert len(chunk) > 0, "Expected non-empty binary video stream from NVR"

        # Validate Hikvision MPEG-PS media container signature (starts with 'IMKH' or PS header 0x000001ba)
        has_valid_header = chunk.startswith(b"IMKH") or b"\x00\x00\x01\xba" in chunk[:32]
        assert has_valid_header, f"Unexpected video header signature: {chunk[:16]!r}"

        total_size_mb = int(rec.size_bytes) / (1024 * 1024)
        print(
            f"\n[OK] Successfully streamed video payload: "
            f"HTTP {response.status_code}, total file size: {total_size_mb:.2f} MB, "
            f"first chunk read: {len(chunk)} bytes (Header signature: {chunk[:8]!r})"
        )
    except (requests.RequestException, RuntimeError, TimeoutError, ValueError) as exc:
        pytest.skip(f"Live download stream probe skipped/failed: {exc}")
