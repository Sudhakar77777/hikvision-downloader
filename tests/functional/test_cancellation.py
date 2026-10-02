import threading
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from hikvision_downloader.core.downloads import download_recording, download_recordings
from hikvision_downloader.core.models import (
    ByteCount,
    ISODatetimeStr,
    Recording,
    TrackId,
)


def test_download_recording_cancelled_before_start(tmp_path: Path, mocker: MockerFixture) -> None:
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

    mock_request = mocker.patch("hikvision_downloader.core.downloads.request_with_retry")
    session = MagicMock()

    success, _duration, actual_size, is_skipped, err = download_recording(
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
    assert is_skipped is False
    assert actual_size == ByteCount(0)
    assert err == "Download cancelled"
    assert not dest.exists()
    mock_request.assert_not_called()


def test_download_recording_cancelled_during_streaming(tmp_path: Path, mocker: MockerFixture) -> None:
    destination = tmp_path / "1_ch01.mp4"
    part_file = destination.with_suffix(".mp4.part")

    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01.mp4",
        size_bytes=ByteCount(4096),
        playback_uri="rtsp://192.168.1.100/track",
    )

    cancel_event = threading.Event()

    def iter_content_with_cancellation(chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        yield b"A" * 1024
        # Trigger cancellation during the stream
        cancel_event.set()
        yield b"B" * 1024

    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None
    mock_response.iter_content = iter_content_with_cancellation

    mocker.patch("hikvision_downloader.core.downloads.request_with_retry", return_value=mock_response)

    session = MagicMock()
    success, _duration, actual_size, _is_skipped, err = download_recording(
        session=session,
        host="192.168.1.100",
        recording=rec,
        track_id=TrackId(101),
        destination=destination,
        current_index=1,
        total_files=1,
        cancel_event=cancel_event,
    )

    assert success is False
    assert actual_size == ByteCount(0)
    assert err == "Download cancelled"
    # Ensure temporary .part file was cleaned up and final file was not created
    assert not part_file.exists()
    assert not destination.exists()


def test_download_recordings_batch_cancelled_before_batch(tmp_path: Path) -> None:
    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01_1.mp4",
        size_bytes=ByteCount(1000),
        playback_uri="rtsp://192.168.1.100/track1",
    )

    cancel_event = threading.Event()
    cancel_event.set()

    session = MagicMock()
    result = download_recordings(
        session=session,
        host="192.168.1.100",
        recordings=[rec],
        track_id=TrackId(101),
        output_dir=tmp_path,
        start=1,
        count=1,
        cancel_event=cancel_event,
    )

    assert result.success is False
    assert result.total_files == 1
    assert result.downloaded_files == 0
    assert result.failed_index == 1
    assert result.error_message == "Batch download cancelled by user"


def test_download_recordings_batch_cancelled_after_first_file(tmp_path: Path, mocker: MockerFixture) -> None:
    recs = [
        Recording(
            start=ISODatetimeStr("2026-09-15T00:00:00Z"),
            end=ISODatetimeStr("2026-09-15T00:15:00Z"),
            name="ch01_1.mp4",
            size_bytes=ByteCount(1000),
            playback_uri="rtsp://192.168.1.100/track1",
        ),
        Recording(
            start=ISODatetimeStr("2026-09-15T00:15:00Z"),
            end=ISODatetimeStr("2026-09-15T00:30:00Z"),
            name="ch01_2.mp4",
            size_bytes=ByteCount(2000),
            playback_uri="rtsp://192.168.1.100/track2",
        ),
    ]

    cancel_event = threading.Event()

    def mock_download_single(
        *_args: object,
        **kwargs: object,
    ) -> tuple[bool, float, ByteCount, bool, str | None]:
        destination = kwargs.get("destination")
        assert isinstance(destination, Path)
        if destination.name == "1_ch01_1.mp4":
            # Set cancellation right after first download completes
            cancel_event.set()
            return True, 1.0, ByteCount(1000), False, None
        return True, 1.0, ByteCount(2000), False, None

    mocker.patch("hikvision_downloader.core.downloads.download_recording", side_effect=mock_download_single)

    session = MagicMock()
    result = download_recordings(
        session=session,
        host="192.168.1.100",
        recordings=recs,
        track_id=TrackId(101),
        output_dir=tmp_path,
        start=1,
        count=2,
        cancel_event=cancel_event,
    )

    assert result.success is False
    assert result.total_files == 2
    assert result.downloaded_files == 1
    assert result.skipped_files == 0
    assert result.failed_index == 2
    assert result.error_message == "Batch download cancelled by user"
