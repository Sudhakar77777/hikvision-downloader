import signal
import threading
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from hikvision_downloader.cli.app import (
    build_argument_parser,
    parse_date_spec,
    parse_range_spec,
    parse_stream_type,
    resolve_camera,
    run_app,
    setup_signal_handler,
)
from hikvision_downloader.cli.formatters import display_abort_notice, display_error
from hikvision_downloader.core.models import (
    ByteCount,
    Camera,
    CameraNumber,
    DownloadResult,
    ISODatetimeStr,
    Recording,
    StreamType,
    TrackId,
)


@pytest.fixture
def sample_cameras() -> dict[CameraNumber, Camera]:
    """Provide sample dictionary of cameras for testing."""
    return {
        CameraNumber(1): Camera(
            number=CameraNumber(1),
            name="FrontGate",
            ip_address="192.168.1.100",
            main_track=TrackId(101),
            sub_track=TrackId(102),
        ),
        CameraNumber(2): Camera(
            number=CameraNumber(2),
            name="BackYard",
            ip_address="192.168.1.101",
            main_track=TrackId(201),
            sub_track=TrackId(202),
        ),
    }


# ============================================================
# Argument Parser Tests
# ============================================================


def test_argument_parser_defaults() -> None:
    parser = build_argument_parser()
    args = parser.parse_args([])

    assert args.host is None
    assert args.date is None
    assert args.camera is None
    assert args.stream is None
    assert args.range is None
    assert args.output_dir is None
    assert args.non_interactive is False


def test_argument_parser_all_flags() -> None:
    parser = build_argument_parser()
    args = parser.parse_args(
        [
            "--host",
            "192.168.1.200",
            "--date",
            "2024-03-15",
            "--camera",
            "1",
            "--stream",
            "main",
            "--range",
            "1-10",
            "--output-dir",
            "/tmp/cctv",
            "--non-interactive",
        ]
    )

    assert args.host == "192.168.1.200"
    assert args.date == "2024-03-15"
    assert args.camera == "1"
    assert args.stream == "main"
    assert args.range == "1-10"
    assert args.output_dir == Path("/tmp/cctv")
    assert args.non_interactive is True


def test_argument_parser_help_and_epilog(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_argument_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "hikvision-downloader" in captured.out
    assert "Ctrl+C" in captured.out
    assert "--non-interactive" in captured.out
    assert ".part" in captured.out


# ============================================================
# Parser Utilities Tests
# ============================================================


def test_parse_date_spec_valid() -> None:
    parsed = parse_date_spec("2024-03-15")
    assert parsed == date(2024, 3, 15)


def test_parse_date_spec_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid date"):
        parse_date_spec("invalid-date")

    with pytest.raises(ValueError, match="Invalid date"):
        parse_date_spec("2024/03/15")


def test_parse_stream_type_valid() -> None:
    assert parse_stream_type("main") == StreamType.MAIN
    assert parse_stream_type("MAIN") == StreamType.MAIN
    assert parse_stream_type("sub") == StreamType.SUB
    assert parse_stream_type("SUB") == StreamType.SUB


def test_parse_stream_type_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid stream type"):
        parse_stream_type("ultra")


def test_parse_range_spec_all() -> None:
    assert parse_range_spec(None, 50) == (1, 50)
    assert parse_range_spec("all", 50) == (1, 50)
    assert parse_range_spec("ALL", 50) == (1, 50)


def test_parse_range_spec_hyphen_and_colon() -> None:
    assert parse_range_spec("1-10", 50) == (1, 10)
    assert parse_range_spec("5-15", 50) == (5, 11)
    assert parse_range_spec("1:10", 50) == (1, 10)


def test_parse_range_spec_space_syntax() -> None:
    assert parse_range_spec("1 10", 50) == (1, 10)
    assert parse_range_spec("16 2", 50) == (16, 2)


def test_parse_range_spec_single_number() -> None:
    assert parse_range_spec("5", 50) == (5, 1)


def test_parse_range_spec_invalid() -> None:
    with pytest.raises(ValueError, match="empty recording list"):
        parse_range_spec("1-5", 0)

    with pytest.raises(ValueError, match="Start index must be >= 1"):
        parse_range_spec("0-5", 50)

    with pytest.raises(ValueError, match="End index.*cannot be less than start index"):
        parse_range_spec("10-5", 50)

    with pytest.raises(ValueError, match="exceeds available recordings count"):
        parse_range_spec("1-60", 50)

    with pytest.raises(ValueError, match="Count must be >= 1"):
        parse_range_spec("1 0", 50)

    with pytest.raises(ValueError, match="exceeds available recordings count"):
        parse_range_spec("45 10", 50)

    with pytest.raises(ValueError, match="out of bounds"):
        parse_range_spec("55", 50)

    with pytest.raises(ValueError, match="Invalid range format"):
        parse_range_spec("foo-bar-baz", 50)

    with pytest.raises(ValueError, match="Invalid range specification"):
        parse_range_spec("invalid_range", 50)



# ============================================================
# Camera Resolver Tests
# ============================================================


def test_resolve_camera_by_number(sample_cameras: dict[CameraNumber, Camera]) -> None:
    cam = resolve_camera(sample_cameras, 1)
    assert cam.name == "FrontGate"

    cam_str = resolve_camera(sample_cameras, "2")
    assert cam_str.name == "BackYard"


def test_resolve_camera_by_name(sample_cameras: dict[CameraNumber, Camera]) -> None:
    cam = resolve_camera(sample_cameras, "FrontGate")
    assert cam.number == CameraNumber(1)

    cam_lower = resolve_camera(sample_cameras, "backyard")
    assert cam_lower.number == CameraNumber(2)

    cam_display = resolve_camera(sample_cameras, "D1 FrontGate")
    assert cam_display.number == CameraNumber(1)

    cam_archive = resolve_camera(sample_cameras, "D2_BackYard")
    assert cam_archive.number == CameraNumber(2)


def test_resolve_camera_not_found(sample_cameras: dict[CameraNumber, Camera]) -> None:
    with pytest.raises(ValueError, match="Camera 'NonExistent' not found"):
        resolve_camera(sample_cameras, "NonExistent")

    with pytest.raises(ValueError, match="Camera '99' not found"):
        resolve_camera(sample_cameras, 99)


# ============================================================
# Signal Interruption & Formatters Tests
# ============================================================


def test_display_abort_notice(capsys: pytest.CaptureFixture[str]) -> None:
    display_abort_notice()
    captured = capsys.readouterr()
    assert "[ABORTED]" in captured.out
    assert "Ctrl+C" in captured.out


def test_display_error(capsys: pytest.CaptureFixture[str]) -> None:
    display_error("Something went wrong")
    captured = capsys.readouterr()
    assert "ERROR: Something went wrong" in captured.out


def test_setup_signal_handler() -> None:
    cancel_event = threading.Event()
    setup_signal_handler(cancel_event)

    # Retrieve current handler for SIGINT
    handler = signal.getsignal(signal.SIGINT)
    assert callable(handler)

    # Simulate SIGINT signal delivery
    handler(signal.SIGINT, None)
    assert cancel_event.is_set()


# ============================================================
# CLI Workflow & Headless Mode Execution Tests
# ============================================================


def test_run_app_missing_host(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch("hikvision_downloader.cli.app.NVR_HOST", None):
        exit_code = run_app([])
        assert exit_code == 1


def test_run_app_non_interactive_missing_date(sample_cameras: dict[CameraNumber, Camera]) -> None:
    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", return_value=sample_cameras),
        patch("hikvision_downloader.cli.app.make_session"),
    ):
        exit_code = run_app(["--non-interactive", "--camera", "1", "--stream", "main"])
        assert exit_code == 1


def test_run_app_non_interactive_missing_camera(sample_cameras: dict[CameraNumber, Camera]) -> None:
    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", return_value=sample_cameras),
        patch("hikvision_downloader.cli.app.make_session"),
    ):
        exit_code = run_app(["--non-interactive", "--date", "2024-03-15", "--stream", "main"])
        assert exit_code == 1


def test_run_app_non_interactive_missing_stream(sample_cameras: dict[CameraNumber, Camera]) -> None:
    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", return_value=sample_cameras),
        patch("hikvision_downloader.cli.app.make_session"),
    ):
        exit_code = run_app(["--non-interactive", "--date", "2024-03-15", "--camera", "1"])
        assert exit_code == 1


def test_run_app_non_interactive_success(sample_cameras: dict[CameraNumber, Camera], tmp_path: Path) -> None:
    mock_recordings = [
        Recording(
            start=ISODatetimeStr("2024-03-15T00:00:00Z"),
            end=ISODatetimeStr("2024-03-15T00:15:00Z"),
            name="segment_1.mp4",
            size_bytes=ByteCount(10_000_000),
            playback_uri="rtsp://192.168.1.100/track/101",
        )
    ]
    mock_result = DownloadResult(
        success=True,
        total_files=1,
        downloaded_files=1,
        skipped_files=0,
        downloaded_bytes=ByteCount(10_000_000),
        total_duration_seconds=2.0,
    )

    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", return_value=sample_cameras),
        patch("hikvision_downloader.cli.app.make_session"),
        patch("hikvision_downloader.cli.app.get_all_recordings", return_value=mock_recordings),
        patch("hikvision_downloader.cli.app.save_recording_list", return_value=tmp_path / "recordings.csv"),
        patch("hikvision_downloader.cli.app.download_recordings", return_value=mock_result),
    ):
        exit_code = run_app(
            [
                "--non-interactive",
                "--date",
                "2024-03-15",
                "--camera",
                "1",
                "--stream",
                "main",
                "--range",
                "all",
                "--output-dir",
                str(tmp_path),
            ]
        )
        assert exit_code == 0


def test_run_app_download_failure(sample_cameras: dict[CameraNumber, Camera], tmp_path: Path) -> None:
    mock_recordings = [
        Recording(
            start=ISODatetimeStr("2024-03-15T00:00:00Z"),
            end=ISODatetimeStr("2024-03-15T00:15:00Z"),
            name="segment_1.mp4",
            size_bytes=ByteCount(10_000_000),
            playback_uri="rtsp://192.168.1.100/track/101",
        )
    ]
    mock_result = DownloadResult(
        success=False,
        total_files=1,
        downloaded_files=0,
        skipped_files=0,
        downloaded_bytes=ByteCount(0),
        total_duration_seconds=0.5,
        failed_index=1,
        error_message="Connection timed out",
    )

    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", return_value=sample_cameras),
        patch("hikvision_downloader.cli.app.make_session"),
        patch("hikvision_downloader.cli.app.get_all_recordings", return_value=mock_recordings),
        patch("hikvision_downloader.cli.app.save_recording_list", return_value=tmp_path / "recordings.csv"),
        patch("hikvision_downloader.cli.app.download_recordings", return_value=mock_result),
    ):
        exit_code = run_app(
            [
                "--non-interactive",
                "--date",
                "2024-03-15",
                "--camera",
                "1",
                "--stream",
                "main",
            ]
        )
        assert exit_code == 1


def test_run_app_keyboard_interrupt_handled(sample_cameras: dict[CameraNumber, Camera]) -> None:
    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", side_effect=KeyboardInterrupt),
    ):
        exit_code = run_app([])
        assert exit_code == 130


def test_run_app_interactive_date_cancelled(sample_cameras: dict[CameraNumber, Camera]) -> None:
    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", return_value=sample_cameras),
        patch("hikvision_downloader.cli.app.make_session"),
        patch("hikvision_downloader.cli.app.discover_dates", return_value={}),
        patch("hikvision_downloader.cli.app.ask_recording_date", return_value=None),
    ):
        exit_code = run_app([])
        assert exit_code == 0


def test_run_app_interactive_camera_cancelled(sample_cameras: dict[CameraNumber, Camera]) -> None:
    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", return_value=sample_cameras),
        patch("hikvision_downloader.cli.app.make_session"),
        patch("hikvision_downloader.cli.app.discover_dates", return_value={}),
        patch("hikvision_downloader.cli.app.ask_recording_date", return_value=date(2024, 3, 15)),
        patch("hikvision_downloader.cli.app.ask_camera", return_value=None),
    ):
        exit_code = run_app([])
        assert exit_code == 0


def test_run_app_interactive_stream_cancelled(sample_cameras: dict[CameraNumber, Camera]) -> None:
    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", return_value=sample_cameras),
        patch("hikvision_downloader.cli.app.make_session"),
        patch("hikvision_downloader.cli.app.discover_dates", return_value={}),
        patch("hikvision_downloader.cli.app.ask_recording_date", return_value=date(2024, 3, 15)),
        patch("hikvision_downloader.cli.app.ask_camera", return_value=sample_cameras[CameraNumber(1)]),
        patch("hikvision_downloader.cli.app.ask_stream", return_value=None),
    ):
        exit_code = run_app([])
        assert exit_code == 0


def test_run_app_interactive_no_recordings(sample_cameras: dict[CameraNumber, Camera]) -> None:
    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", return_value=sample_cameras),
        patch("hikvision_downloader.cli.app.make_session"),
        patch("hikvision_downloader.cli.app.discover_dates", return_value={}),
        patch("hikvision_downloader.cli.app.ask_recording_date", return_value=date(2024, 3, 15)),
        patch("hikvision_downloader.cli.app.ask_camera", return_value=sample_cameras[CameraNumber(1)]),
        patch("hikvision_downloader.cli.app.ask_stream", return_value=StreamType.MAIN),
        patch("hikvision_downloader.cli.app.search_recordings_for_date", return_value=None),
    ):
        exit_code = run_app([])
        assert exit_code == 0


def test_run_app_interactive_selection_declined(sample_cameras: dict[CameraNumber, Camera], tmp_path: Path) -> None:
    mock_recordings = [
        Recording(
            start=ISODatetimeStr("2024-03-15T00:00:00Z"),
            end=ISODatetimeStr("2024-03-15T00:15:00Z"),
            name="segment_1.mp4",
            size_bytes=ByteCount(10_000_000),
            playback_uri="rtsp://192.168.1.100/track/101",
        )
    ]
    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", return_value=sample_cameras),
        patch("hikvision_downloader.cli.app.make_session"),
        patch("hikvision_downloader.cli.app.discover_dates", return_value={}),
        patch("hikvision_downloader.cli.app.ask_recording_date", return_value=date(2024, 3, 15)),
        patch("hikvision_downloader.cli.app.ask_camera", return_value=sample_cameras[CameraNumber(1)]),
        patch("hikvision_downloader.cli.app.ask_stream", return_value=StreamType.MAIN),
        patch("hikvision_downloader.cli.app.search_recordings_for_date", return_value=(mock_recordings, 1.0)),
        patch("hikvision_downloader.cli.app.save_recording_list", return_value=tmp_path / "recordings.csv"),
        patch("hikvision_downloader.cli.app.ask_download_selection", return_value=(1, 1)),
        patch("hikvision_downloader.cli.app.confirm_download", return_value=False),
    ):
        exit_code = run_app([])
        assert exit_code == 0


def test_run_app_cancellation_during_download(sample_cameras: dict[CameraNumber, Camera], tmp_path: Path) -> None:
    mock_recordings = [
        Recording(
            start=ISODatetimeStr("2024-03-15T00:00:00Z"),
            end=ISODatetimeStr("2024-03-15T00:15:00Z"),
            name="segment_1.mp4",
            size_bytes=ByteCount(10_000_000),
            playback_uri="rtsp://192.168.1.100/track/101",
        )
    ]

    def fake_download(*args: object, **kwargs: object) -> DownloadResult:
        cancel_evt = kwargs.get("cancel_event")
        if isinstance(cancel_evt, threading.Event):
            cancel_evt.set()
        return DownloadResult(
            success=False,
            total_files=1,
            downloaded_files=0,
            skipped_files=0,
            downloaded_bytes=ByteCount(0),
            total_duration_seconds=0.5,
            failed_index=1,
            error_message="Batch download cancelled by user",
        )

    with (
        patch("hikvision_downloader.cli.app.NVR_HOST", "192.168.1.100"),
        patch("hikvision_downloader.cli.app.load_cameras", return_value=sample_cameras),
        patch("hikvision_downloader.cli.app.make_session"),
        patch("hikvision_downloader.cli.app.get_all_recordings", return_value=mock_recordings),
        patch("hikvision_downloader.cli.app.save_recording_list", return_value=tmp_path / "recordings.csv"),
        patch("hikvision_downloader.cli.app.download_recordings", side_effect=fake_download),
    ):
        exit_code = run_app(
            [
                "--non-interactive",
                "--date",
                "2024-03-15",
                "--camera",
                "1",
                "--stream",
                "main",
            ]
        )
        assert exit_code == 130

