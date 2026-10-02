from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from pytest_mock import MockerFixture

from hikvision_downloader.core.downloads import (
    build_download_url,
    download_recording,
    download_recordings,
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
    assert format_duration(-5.0) == "0.0s"
    assert format_duration(45.2) == "45.2s"
    assert format_duration(95.0) == "1m 35s"
    assert format_duration(3665.0) == "1h 01m 05s"


def test_build_download_url() -> None:
    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01.mp4",
        size_bytes=ByteCount(1024),
        playback_uri="rtsp://192.168.1.100/track",
    )
    url = build_download_url("192.168.1.100", rec, TrackId(101))
    assert url.startswith("http://192.168.1.100/ISAPI/ContentMgmt/download?")
    assert "tracks/101" in url
    assert "starttime=2026-09-15 00:00:00" in url
    assert "endtime=2026-09-15 00:15:00" in url
    assert "name=ch01.mp4" in url
    assert "size=1024" in url
    assert "onlyVerification=true" in url


def test_download_recording_chunk_streaming(tmp_path: Path, mocker: MockerFixture) -> None:
    destination = tmp_path / "1_ch01.mp4"
    part_file = destination.with_suffix(".mp4.part")

    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01.mp4",
        size_bytes=ByteCount(2048),
        playback_uri="rtsp://192.168.1.100/track",
    )

    chunks: list[bytes] = [b"A" * 1024, b"B" * 1024]

    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None

    def iter_content_mock(chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        assert part_file.exists()  # Part file must exist during streaming
        yield from chunks

    mock_response.iter_content = iter_content_mock
    mocker.patch("hikvision_downloader.core.downloads.request_with_retry", return_value=mock_response)

    progress_events: list[DownloadProgress] = []
    session = MagicMock()

    success, duration, actual_size, is_skipped, error_msg = download_recording(
        session=session,
        host="192.168.1.100",
        recording=rec,
        track_id=TrackId(101),
        destination=destination,
        current_index=1,
        total_files=1,
        progress_callback=progress_events.append,
    )

    assert success is True
    assert duration >= 0.0
    assert actual_size == ByteCount(2048)
    assert is_skipped is False
    assert error_msg is None

    # Verify atomic rename
    assert not part_file.exists()
    assert destination.exists()
    assert destination.read_bytes() == b"A" * 1024 + b"B" * 1024

    # Verify progress events (initial 0-byte start and final completion)
    assert len(progress_events) >= 2
    assert progress_events[0].current_index == 1
    assert progress_events[0].bytes_downloaded == ByteCount(0)
    assert progress_events[0].is_completed is False
    assert progress_events[-1].current_index == 1
    assert progress_events[-1].bytes_downloaded == ByteCount(2048)
    assert progress_events[-1].is_completed is True
    assert progress_events[-1].is_skipped is False


def test_download_recording_skipped_if_exists(tmp_path: Path, mocker: MockerFixture) -> None:
    dest = tmp_path / "1_ch01.mp4"
    dest.write_bytes(b"existing video payload")

    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01.mp4",
        size_bytes=ByteCount(len(b"existing video payload")),
        playback_uri="rtsp://192.168.1.100/track",
    )

    mock_request = mocker.patch("hikvision_downloader.core.downloads.request_with_retry")
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
    assert actual_size == ByteCount(len(b"existing video payload"))
    assert len(progress_events) == 1
    assert progress_events[0].is_skipped is True
    mock_request.assert_not_called()


def test_download_recording_invalid_filename(tmp_path: Path) -> None:
    dest = tmp_path / "1_unknown.mp4"
    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="unknown",
        size_bytes=ByteCount(1024),
        playback_uri="rtsp://192.168.1.100/track",
    )

    session = MagicMock()
    success, _duration, actual_size, _is_skipped, error_msg = download_recording(
        session=session,
        host="192.168.1.100",
        recording=rec,
        track_id=TrackId(101),
        destination=dest,
        current_index=1,
        total_files=1,
    )

    assert success is False
    assert actual_size == ByteCount(0)
    assert error_msg == "Recording has invalid filename"
    assert not dest.exists()


def test_download_recording_zero_byte_error(tmp_path: Path, mocker: MockerFixture) -> None:
    destination = tmp_path / "1_ch01.mp4"
    part_file = destination.with_suffix(".mp4.part")

    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01.mp4",
        size_bytes=ByteCount(2048),
        playback_uri="rtsp://192.168.1.100/track",
    )

    def iter_content_empty(*_args: object, **_kwargs: object) -> Iterator[bytes]:
        return iter([])

    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None
    mock_response.iter_content = iter_content_empty
    mocker.patch("hikvision_downloader.core.downloads.request_with_retry", return_value=mock_response)

    session = MagicMock()
    success, _duration, actual_size, _is_skipped, error_msg = download_recording(
        session=session,
        host="192.168.1.100",
        recording=rec,
        track_id=TrackId(101),
        destination=destination,
        current_index=1,
        total_files=1,
    )

    assert success is False
    assert actual_size == ByteCount(0)
    assert error_msg == "Empty file received from NVR"
    assert not destination.exists()
    assert not part_file.exists()


def test_download_recording_network_error(tmp_path: Path, mocker: MockerFixture) -> None:
    destination = tmp_path / "1_ch01.mp4"
    part_file = destination.with_suffix(".mp4.part")

    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01.mp4",
        size_bytes=ByteCount(2048),
        playback_uri="rtsp://192.168.1.100/track",
    )

    mocker.patch(
        "hikvision_downloader.core.downloads.request_with_retry",
        side_effect=requests.ConnectionError("NVR reset connection"),
    )

    session = MagicMock()
    success, _duration, _actual_size, _is_skipped, error_msg = download_recording(
        session=session,
        host="192.168.1.100",
        recording=rec,
        track_id=TrackId(101),
        destination=destination,
        current_index=1,
        total_files=1,
    )

    assert success is False
    assert "NVR reset connection" in str(error_msg)
    assert not destination.exists()
    assert not part_file.exists()


def test_download_recordings_batch_bounds_validation() -> None:
    rec = Recording(
        start=ISODatetimeStr("2026-09-15T00:00:00Z"),
        end=ISODatetimeStr("2026-09-15T00:15:00Z"),
        name="ch01.mp4",
        size_bytes=ByteCount(100),
        playback_uri="rtsp://192.168.1.100/track",
    )
    session = MagicMock()
    output_dir = Path("/tmp")

    with pytest.raises(ValueError, match="Start index 0 out of bounds"):
        download_recordings(session, "192.168.1.100", [rec], TrackId(101), output_dir, start=0, count=1)

    with pytest.raises(ValueError, match="Start index 2 out of bounds"):
        download_recordings(session, "192.168.1.100", [rec], TrackId(101), output_dir, start=2, count=1)

    with pytest.raises(ValueError, match="Count must be >= 1"):
        download_recordings(session, "192.168.1.100", [rec], TrackId(101), output_dir, start=1, count=0)

    with pytest.raises(ValueError, match="exceeds total recordings"):
        download_recordings(session, "192.168.1.100", [rec], TrackId(101), output_dir, start=1, count=2)


def test_download_recordings_batch_success(tmp_path: Path, mocker: MockerFixture) -> None:
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

    # Pre-create file 1 to test skip in batch
    file1 = tmp_path / "1_ch01_1.mp4"
    file1.write_bytes(b"existing file 1")

    # Mock download_recording for file 2
    def mock_download_single(
        *_args: object,
        **kwargs: object,
    ) -> tuple[bool, float, ByteCount, bool, str | None]:
        destination = kwargs.get("destination")
        assert isinstance(destination, Path)
        if destination.name == "1_ch01_1.mp4":
            return True, 0.0, ByteCount(15), True, None
        return True, 1.5, ByteCount(2000), False, None

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
    )

    assert result.success is True
    assert result.total_files == 2
    assert result.downloaded_files == 1
    assert result.skipped_files == 1
    assert result.downloaded_bytes == ByteCount(2000)
    assert result.failed_index is None
    assert result.error_message is None


def test_download_recordings_batch_midway_failure(tmp_path: Path, mocker: MockerFixture) -> None:
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

    # First file succeeds, second file fails
    def mock_download_single(
        *_args: object,
        **kwargs: object,
    ) -> tuple[bool, float, ByteCount, bool, str | None]:
        destination = kwargs.get("destination")
        assert isinstance(destination, Path)
        if destination.name == "1_ch01_1.mp4":
            return True, 1.0, ByteCount(1000), False, None
        return False, 0.5, ByteCount(0), False, "Connection reset by peer"

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
    )

    assert result.success is False
    assert result.total_files == 2
    assert result.downloaded_files == 1
    assert result.skipped_files == 0
    assert result.failed_index == 2
    assert result.error_message == "Connection reset by peer"
