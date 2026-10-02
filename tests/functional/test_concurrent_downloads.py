import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from hikvision_downloader.core.downloads import download_recordings_concurrent
from hikvision_downloader.core.models import (
    ByteCount,
    DownloadProgress,
    ISODatetimeStr,
    MegabitsPerSecond,
    Recording,
    TrackId,
)


@pytest.fixture
def sample_recordings() -> list[Recording]:
    return [
        Recording(
            start=ISODatetimeStr("2026-09-15T00:00:00Z"),
            end=ISODatetimeStr("2026-09-15T00:15:00Z"),
            name="segment_1.mp4",
            size_bytes=ByteCount(1024),
            playback_uri="rtsp://192.168.1.100/track/101",
        ),
        Recording(
            start=ISODatetimeStr("2026-09-15T00:15:00Z"),
            end=ISODatetimeStr("2026-09-15T00:30:00Z"),
            name="segment_2.mp4",
            size_bytes=ByteCount(2048),
            playback_uri="rtsp://192.168.1.100/track/101",
        ),
        Recording(
            start=ISODatetimeStr("2026-09-15T00:30:00Z"),
            end=ISODatetimeStr("2026-09-15T00:45:00Z"),
            name="segment_3.mp4",
            size_bytes=ByteCount(4096),
            playback_uri="rtsp://192.168.1.100/track/101",
        ),
    ]


def test_concurrent_downloads_bounds_validation(sample_recordings: list[Recording]) -> None:
    session = MagicMock()
    output_dir = Path("/tmp")

    with pytest.raises(ValueError, match="Start index 0 out of bounds"):
        download_recordings_concurrent(session, "192.168.1.100", sample_recordings, TrackId(101), output_dir, start=0, count=1)

    with pytest.raises(ValueError, match="Count must be >= 1"):
        download_recordings_concurrent(session, "192.168.1.100", sample_recordings, TrackId(101), output_dir, start=1, count=0)

    with pytest.raises(ValueError, match="exceeds total recordings"):
        download_recordings_concurrent(session, "192.168.1.100", sample_recordings, TrackId(101), output_dir, start=2, count=3)


def test_concurrent_downloads_success(
    tmp_path: Path,
    sample_recordings: list[Recording],
    mocker: MockerFixture,
) -> None:
    # Pre-create file 1 to test skipping
    file1 = tmp_path / "1_segment_1.mp4"
    file1.write_bytes(b"X" * 1024)

    def mock_download_single(
        *_args: object,
        **kwargs: object,
    ) -> tuple[bool, float, ByteCount, bool, str | None]:
        destination = kwargs.get("destination")
        assert isinstance(destination, Path)
        current_index = kwargs.get("current_index", 1)
        cb = kwargs.get("progress_callback")

        if destination.name == "1_segment_1.mp4":
            if callable(cb):
                cb(
                    DownloadProgress(
                        current_index=int(str(current_index)),
                        total_files=3,
                        filename=destination.name,
                        bytes_downloaded=ByteCount(1024),
                        file_size_bytes=ByteCount(1024),
                        speed_mbps=MegabitsPerSecond(0.0),
                        elapsed_seconds=0.0,
                        is_skipped=True,
                    )
                )
            return True, 0.0, ByteCount(1024), True, None

        # Simulate streaming file
        destination.write_bytes(b"video data")
        if callable(cb):
            cb(
                DownloadProgress(
                    current_index=int(str(current_index)),
                    total_files=3,
                    filename=destination.name,
                    bytes_downloaded=ByteCount(2048),
                    file_size_bytes=ByteCount(2048),
                    speed_mbps=MegabitsPerSecond(10.0),
                    elapsed_seconds=0.5,
                    is_skipped=False,
                )
            )
        return True, 0.5, ByteCount(2048), False, None

    mocker.patch("hikvision_downloader.core.downloads.download_recording", side_effect=mock_download_single)

    session = MagicMock()
    progress_list: list[DownloadProgress] = []

    result = download_recordings_concurrent(
        session=session,
        host="192.168.1.100",
        recordings=sample_recordings,
        track_id=TrackId(101),
        output_dir=tmp_path,
        start=1,
        count=3,
        max_workers=3,
        port=80,
        progress_callback=progress_list.append,
    )

    assert result.success is True
    assert result.total_files == 3
    assert result.downloaded_files == 2
    assert result.skipped_files == 1
    assert result.downloaded_bytes == ByteCount(4096)
    assert len(progress_list) == 3


def test_concurrent_downloads_worker_clamp(
    tmp_path: Path,
    sample_recordings: list[Recording],
    mocker: MockerFixture,
) -> None:
    def fake_download(*_args: object, **_kwargs: object) -> tuple[bool, float, ByteCount, bool, str | None]:
        return True, 0.1, ByteCount(1024), False, None

    mocker.patch("hikvision_downloader.core.downloads.download_recording", side_effect=fake_download)

    session = MagicMock()
    spy_tp = mocker.spy(ThreadPoolExecutor, "__init__")

    download_recordings_concurrent(
        session=session,
        host="192.168.1.100",
        recordings=sample_recordings,
        track_id=TrackId(101),
        output_dir=tmp_path,
        start=1,
        count=3,
        max_workers=10,
    )

    # Check max_workers passed to ThreadPoolExecutor
    assert spy_tp.call_args[1]["max_workers"] == 4


def test_concurrent_downloads_cancellation(
    tmp_path: Path,
    sample_recordings: list[Recording],
    mocker: MockerFixture,
) -> None:
    cancel_event = threading.Event()
    cancel_event.set()

    session = MagicMock()
    result = download_recordings_concurrent(
        session=session,
        host="192.168.1.100",
        recordings=sample_recordings,
        track_id=TrackId(101),
        output_dir=tmp_path,
        start=1,
        count=3,
        cancel_event=cancel_event,
    )

    assert result.success is False
    assert result.error_message == "Download cancelled"


def test_concurrent_downloads_mid_batch_failure(
    tmp_path: Path,
    sample_recordings: list[Recording],
    mocker: MockerFixture,
) -> None:
    def fake_download(*_args: object, **kwargs: object) -> tuple[bool, float, ByteCount, bool, str | None]:
        destination = kwargs.get("destination")
        assert isinstance(destination, Path)
        if "segment_2" in destination.name:
            return False, 0.2, ByteCount(0), False, "Network socket closed"
        return True, 0.1, ByteCount(1024), False, None

    mocker.patch("hikvision_downloader.core.downloads.download_recording", side_effect=fake_download)

    session = MagicMock()
    result = download_recordings_concurrent(
        session=session,
        host="192.168.1.100",
        recordings=sample_recordings,
        track_id=TrackId(101),
        output_dir=tmp_path,
        start=1,
        count=3,
    )

    assert result.success is False
    assert result.failed_index == 2
    assert result.error_message == "Network socket closed"
