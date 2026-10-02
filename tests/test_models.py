from datetime import date

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


def test_recording_date_valid() -> None:
    rec_date = RecordingDate(year=2026, month=9, day=15)
    assert rec_date.value == date(2026, 9, 15)
    assert rec_date.iso == "2026-09-15"


def test_recording_date_invalid_calendar() -> None:
    with pytest.raises(ValidationError):
        RecordingDate(year=2026, month=2, day=30)

    with pytest.raises(ValidationError):
        RecordingDate(year=1990, month=1, day=1)


def test_recording_model_valid() -> None:
    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01_20260915_000000.mp4",
        size_bytes=ByteCount(104857600),
        playback_uri="rtsp://192.168.1.100/Streaming/tracks/101",
    )
    assert rec.size_mb == 100.0
    assert rec.size == ByteCount(104857600)


def test_recording_model_negative_size() -> None:
    with pytest.raises(ValidationError):
        Recording(
            start=ISODatetimeStr("2026-09-15T00:00:00Z"),
            end=ISODatetimeStr("2026-09-15T00:15:00Z"),
            name="ch01.mp4",
            size_bytes=ByteCount(-1),
            playback_uri="rtsp://...",
        )


def test_download_progress_valid() -> None:
    prog = DownloadProgress(
        current_index=1,
        total_files=5,
        filename="1_ch01.mp4",
        bytes_downloaded=ByteCount(1024),
        file_size_bytes=ByteCount(1024),
        speed_mbps=MegabitsPerSecond(12.5),
        elapsed_seconds=1.2,
        is_skipped=False,
    )
    assert prog.current_index == 1
    assert prog.is_skipped is False


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
