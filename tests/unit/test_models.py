from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from hikvision_downloader.core.models import (
    ByteCount,
    Camera,
    CameraNumber,
    DownloadProgress,
    DownloadResult,
    ISODatetimeStr,
    MegabitsPerSecond,
    NVRAuthCredentials,
    NVRConnectionProfile,
    Recording,
    RecordingDate,
    StreamQuality,
    StreamType,
    TrackId,
)


def test_camera_model_valid() -> None:
    cam = Camera(
        number=CameraNumber(1),
        name="FrontGate",
        ip_address="192.168.1.100",
        main_track=TrackId(101),
        sub_track=TrackId(102),
    )
    assert cam.display_name == "D1 FrontGate"
    assert cam.archive_name == "D1_FrontGate"
    assert cam.stream_quality(StreamType.MAIN) == StreamQuality.HD
    assert cam.stream_quality(StreamType.SUB) == StreamQuality.SD
    assert cam.stream_name(StreamType.MAIN) == "HD"
    assert cam.stream_name(StreamType.SUB) == "SD"
    assert cam.track_id(StreamType.MAIN) == TrackId(101)
    assert cam.track_id(StreamType.SUB) == TrackId(102)


def test_camera_model_validation_errors() -> None:
    with pytest.raises(ValidationError):
        Camera(
            number=CameraNumber(0),
            name="FrontGate",
            ip_address="192.168.1.100",
            main_track=TrackId(101),
            sub_track=TrackId(102),
        )

    with pytest.raises(ValidationError):
        Camera(
            number=CameraNumber(1),
            name="",
            ip_address="192.168.1.100",
            main_track=TrackId(101),
            sub_track=TrackId(102),
        )

    with pytest.raises(ValidationError):
        Camera(
            number=CameraNumber(1),
            name="FrontGate",
            ip_address="",
            main_track=TrackId(101),
            sub_track=TrackId(102),
        )

    with pytest.raises(ValidationError):
        Camera(
            number=CameraNumber(1),
            name="FrontGate",
            ip_address="192.168.1.100",
            main_track=TrackId(0),
            sub_track=TrackId(102),
        )

    with pytest.raises(ValidationError):
        Camera(
            number=CameraNumber(1),
            name="FrontGate",
            ip_address="192.168.1.100",
            main_track=TrackId(101),
            sub_track=TrackId(0),
        )


def test_camera_invalid_stream_type() -> None:
    cam = Camera(
        number=CameraNumber(1),
        name="FrontGate",
        ip_address="192.168.1.100",
        main_track=TrackId(101),
        sub_track=TrackId(102),
    )
    with pytest.raises(ValueError, match="Unknown stream type"):
        cam.stream_quality("invalid")

    with pytest.raises(ValueError, match="Unknown stream type"):
        cam.track_id("invalid")


def test_recording_date_valid() -> None:
    target = (datetime.now(UTC) - timedelta(days=7)).date()
    rec_date = RecordingDate(year=target.year, month=target.month, day=target.day)
    assert rec_date.value == target
    assert rec_date.iso == target.isoformat()


def test_recording_date_invalid_calendar() -> None:
    with pytest.raises(ValidationError):
        RecordingDate(year=2026, month=2, day=30)

    with pytest.raises(ValidationError):
        RecordingDate(year=1990, month=1, day=1)

    with pytest.raises(ValidationError):
        RecordingDate(year=2101, month=1, day=1)

    with pytest.raises(ValidationError):
        RecordingDate(year=2026, month=13, day=1)


def test_recording_model_valid() -> None:
    now = datetime.now(UTC)
    start_dt = now - timedelta(days=7, minutes=15)
    end_dt = now - timedelta(days=7)
    start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    rec = Recording(
        start=ISODatetimeStr(start_iso),
        end=ISODatetimeStr(end_iso),
        name="ch01_segment.mp4",
        size_bytes=ByteCount(104857600),
        playback_uri="rtsp://192.168.1.100/Streaming/tracks/101",
    )
    assert rec.size_mb == 100.0
    assert rec.size == ByteCount(104857600)
    assert rec.start == start_iso
    assert rec.end == end_iso


def test_recording_model_negative_size() -> None:
    now = datetime.now(UTC)
    start_iso = (now - timedelta(days=7, minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    with pytest.raises(ValidationError):
        Recording(
            start=ISODatetimeStr(start_iso),
            end=ISODatetimeStr(end_iso),
            name="ch01.mp4",
            size_bytes=ByteCount(-1),
            playback_uri="rtsp://192.168.1.100/ch01",
        )


def test_nvr_auth_credentials_valid() -> None:
    creds = NVRAuthCredentials(
        host="192.168.1.100",
        username="admin",
        password="secretpassword",  # type: ignore[arg-type]
        port=80,
    )
    assert creds.host == "192.168.1.100"
    assert creds.username == "admin"
    assert creds.password.get_secret_value() == "secretpassword"
    assert "secretpassword" not in str(creds)
    assert creds.port == 80


def test_nvr_auth_credentials_invalid_port() -> None:
    with pytest.raises(ValidationError):
        NVRAuthCredentials(
            host="192.168.1.100",
            username="admin",
            password="secretpassword",  # type: ignore[arg-type]
            port=0,
        )


def test_nvr_connection_profile_valid() -> None:
    profile = NVRConnectionProfile(
        name="HomeNVR",
        host="192.168.1.100",
        username="admin",
    )
    assert profile.name == "HomeNVR"
    assert profile.keyring_service == "hikvision_downloader"


def test_download_progress_valid() -> None:
    now = datetime.now(UTC)
    start_iso = (now - timedelta(days=7, minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    prog = DownloadProgress(
        current_index=1,
        total_files=5,
        filename="1_ch01.mp4",
        bytes_downloaded=ByteCount(1024),
        file_size_bytes=ByteCount(1024),
        speed_mbps=MegabitsPerSecond(12.5),
        elapsed_seconds=1.2,
        is_skipped=False,
        start_time=start_iso,
        end_time=end_iso,
    )
    assert prog.current_index == 1
    assert prog.is_skipped is False
    assert prog.start_time == start_iso
    assert prog.end_time == end_iso


def test_download_progress_invalid() -> None:
    with pytest.raises(ValidationError):
        DownloadProgress(
            current_index=1,
            total_files=5,
            filename="1_ch01.mp4",
            bytes_downloaded=ByteCount(-1),
            file_size_bytes=ByteCount(1024),
            speed_mbps=MegabitsPerSecond(12.5),
            elapsed_seconds=1.2,
        )

    with pytest.raises(ValidationError):
        DownloadProgress(
            current_index=1,
            total_files=5,
            filename="1_ch01.mp4",
            bytes_downloaded=ByteCount(100),
            file_size_bytes=ByteCount(-1),
            speed_mbps=MegabitsPerSecond(12.5),
            elapsed_seconds=1.2,
        )

    with pytest.raises(ValidationError):
        DownloadProgress(
            current_index=1,
            total_files=5,
            filename="1_ch01.mp4",
            bytes_downloaded=ByteCount(100),
            file_size_bytes=ByteCount(1024),
            speed_mbps=MegabitsPerSecond(-1.0),
            elapsed_seconds=1.2,
        )


def test_download_result_valid() -> None:
    res = DownloadResult(
        success=True,
        total_files=5,
        downloaded_files=4,
        skipped_files=1,
        downloaded_bytes=ByteCount(5000000),
        total_duration_seconds=10.5,
    )
    assert res.success is True
    assert res.downloaded_files == 4


def test_download_result_invalid() -> None:
    with pytest.raises(ValidationError):
        DownloadResult(
            success=True,
            total_files=5,
            downloaded_files=4,
            skipped_files=1,
            downloaded_bytes=ByteCount(-50),
            total_duration_seconds=10.5,
        )
