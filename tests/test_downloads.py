import threading
from pathlib import Path
from unittest.mock import MagicMock

from hikvision_downloader.core.downloads import (
    build_download_url,
    download_recording,
    format_duration,
)
from hikvision_downloader.core.models import (
    ByteCount,
    DownloadProgress,
    ISODatetimeStr,
    Recording,
    TrackId,
)


def test_format_duration() -> None:
    assert format_duration(45.2) == "45.2s"
    assert format_duration(95) == "1m 35s"
    assert format_duration(3665) == "1h 01m 05s"


def test_build_download_url() -> None:
    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01.mp4",
        size_bytes=ByteCount(1024),
        playback_uri="rtsp://192.168.1.100/track",
    )
    url = build_download_url("192.168.1.100", rec, TrackId(101))
    assert "http://192.168.1.100/ISAPI/ContentMgmt/download" in url
    assert "tracks/101" in url


def test_download_recording_skipped_if_exists(tmp_path: Path) -> None:
    dest = tmp_path / "1_ch01.mp4"
    dest.write_bytes(b"dummy existing video data")

    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01.mp4",
        size_bytes=ByteCount(25),
        playback_uri="rtsp://192.168.1.100/track",
    )

    progress_events: list[DownloadProgress] = []
    session = MagicMock()

    success, _duration, actual_size, is_skipped, _err = download_recording(
        session=session,
        host="192.168.1.100",
        recording=rec,
        track_id=TrackId(101),
        destination=dest,
        current_index=1,
        total_files=1,
        progress_callback=progress_events.append,
    )

    assert success is True
    assert is_skipped is True
    assert actual_size == ByteCount(25)
    assert len(progress_events) == 1
    assert progress_events[0].is_skipped is True


def test_download_recording_cancellation(tmp_path: Path) -> None:
    dest = tmp_path / "1_ch01.mp4"
    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01.mp4",
        size_bytes=ByteCount(1024),
        playback_uri="rtsp://192.168.1.100/track",
    )

    cancel_event = threading.Event()
    cancel_event.set()

    session = MagicMock()

    success, _duration, _actual_size, _is_skipped, err = download_recording(
        session=session,
        host="192.168.1.100",
        recording=rec,
        track_id=TrackId(101),
        destination=dest,
        current_index=1,
        total_files=1,
        cancel_event=cancel_event,
    )

    assert success is False
    assert err == "Download cancelled"
