import argparse
import getpass
import signal
import sys
import threading
import time
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from types import FrameType
from xml.etree import ElementTree as ET

import requests
from pydantic import SecretStr

from ..config import (
    BATCH_SIZE,
    CAMERA_CONFIG,
    DATE_DISCOVERY_TRACK_ID,
    NVR_AUTH_TYPE,
    NVR_HOST,
    NVR_MAX_WORKERS,
    NVR_PASSWORD,
    NVR_PORT,
    NVR_USERNAME,
    OUTPUT_ROOT,
    TIMEOUT,
)
from ..core.auth import create_authenticated_session
from ..core.cameras import CameraDiscoveryService, format_host_port
from ..core.dates import discover_available_dates
from ..core.downloads import download_recordings_concurrent, format_duration
from ..core.models import Camera, CameraNumber, Recording, RecordingDate, StreamType, TrackId
from ..core.recordings import get_all_recordings, recording_total_size, save_recording_list
from .formatters import (
    display_abort_notice,
    display_available_dates,
    display_download_progress,
    display_download_summary,
    display_error,
    display_header,
    display_recording_list,
    display_selection,
)
from .interactive import (
    ask_camera,
    ask_download_selection,
    ask_recording_date,
    ask_stream,
    confirm_download,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Construct the command-line argument parser with documentation and epilog."""
    parser = argparse.ArgumentParser(
        prog="hikvision-downloader",
        description="Hikvision CCTV NVR Recording Downloader - Headless & Interactive CLI",
        epilog=(
            "Interruption:\n"
            "  Press Ctrl+C at any time to gracefully cancel downloads. In-flight\n"
            "  temporary download files (.part) will be automatically cleaned up\n"
            "  without leaving partial or corrupted files.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Hikvision NVR IP address or hostname (overrides HIKVISION_HOST from .env)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Hikvision NVR HTTP/ISAPI port (overrides HIKVISION_PORT from .env, default: 80)",
    )
    parser.add_argument(
        "-u",
        "--username",
        type=str,
        default=None,
        help="Hikvision NVR username (overrides HIKVISION_USERNAME from .env)",
    )
    parser.add_argument(
        "-p",
        "--password",
        type=str,
        default=None,
        help="Hikvision NVR password (overrides HIKVISION_PASSWORD from .env)",
    )
    parser.add_argument(
        "--auth-type",
        type=str,
        choices=["digest", "basic", "DIGEST", "BASIC"],
        default=None,
        help="HTTP authentication type: 'digest' (default) or 'basic'",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=None,
        help="Number of concurrent download workers (1-4, default: 2)",
    )
    parser.add_argument(
        "--refresh-cameras",
        action="store_true",
        default=False,
        help="Bypass discovery cache and force fresh camera discovery from NVR",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Recording date to download in ISO format (YYYY-MM-DD, e.g. 2024-03-15)",
    )
    parser.add_argument(
        "--camera",
        type=str,
        default=None,
        help="Camera channel number (e.g. 1) or camera name (e.g. FrontGate)",
    )
    parser.add_argument(
        "--stream",
        type=str,
        default=None,
        help="Stream quality or track identifier (e.g. 'main', 'sub', 'third', or custom stream track)",
    )
    parser.add_argument(
        "--range",
        type=str,
        default=None,
        help="Recording range to download: 'all', 'START-END' (e.g. 1-10), or 'START COUNT' (e.g. '1 10')",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Custom destination directory for downloaded recordings",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        default=False,
        help="Run in headless non-interactive mode (fails if required options are omitted)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="hikvision-downloader 0.1.0",
    )

    return parser


def parse_date_spec(date_str: str) -> date:
    """Parse an ISO date string (YYYY-MM-DD) into a date object."""
    try:
        return date.fromisoformat(date_str.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid date '{date_str}'. Expected format: YYYY-MM-DD (e.g. 2024-03-15)") from exc


def parse_stream_type(stream_str: str) -> str | StreamType:
    """Parse a stream type string into a normalized StreamType or custom track identifier."""
    cleaned = stream_str.strip()
    if not cleaned:
        raise ValueError("Stream type cannot be empty.")
    normalized = cleaned.lower()
    if normalized in ("main", "hd", "1"):
        return StreamType.MAIN
    if normalized in ("sub", "sd", "2"):
        return StreamType.SUB
    if normalized in ("third", "preview", "3"):
        return StreamType.THIRD
    if normalized.isdigit():
        return normalized
    if normalized.startswith("stream") and normalized[6:].isdigit():
        return normalized
    if normalized in ("other", "custom"):
        return normalized
    raise ValueError(f"Invalid stream type '{stream_str}'. Expected 'main', 'sub', 'third', track ID, or stream number.")


def parse_range_spec(range_str: str | None, total: int) -> tuple[int, int]:
    """Parse a download range specification into (start, count) tuple."""
    if total < 1:
        raise ValueError("Cannot select recordings from an empty recording list (total=0)")

    if range_str is None or range_str.strip().lower() == "all":
        return 1, total

    cleaned = range_str.strip()

    # Format 1: "START-END" or "START:END" (e.g. "1-10", "1:10")
    if "-" in cleaned or ":" in cleaned:
        delimiter = "-" if "-" in cleaned else ":"
        parts = [p.strip() for p in cleaned.split(delimiter) if p.strip()]
        if len(parts) != 2:
            raise ValueError(f"Invalid range format '{range_str}'. Expected START-END (e.g. '1-10') or 'all'.")
        try:
            start_num = int(parts[0])
            end_num = int(parts[1])
        except ValueError as exc:
            raise ValueError(f"Range values must be integers, got '{range_str}'") from exc

        if start_num < 1:
            raise ValueError(f"Start index must be >= 1, got {start_num}")
        if end_num < start_num:
            raise ValueError(f"End index ({end_num}) cannot be less than start index ({start_num})")
        if end_num > total:
            raise ValueError(f"End index {end_num} exceeds available recordings count {total}")

        return start_num, end_num - start_num + 1

    # Format 2: "START COUNT" (e.g. "1 10")
    parts = cleaned.split()
    if len(parts) == 2:
        try:
            start_num = int(parts[0])
            count_num = int(parts[1])
        except ValueError as exc:
            raise ValueError(f"Range values must be integers, got '{range_str}'") from exc

        if start_num < 1:
            raise ValueError(f"Start index must be >= 1, got {start_num}")
        if count_num < 1:
            raise ValueError(f"Count must be >= 1, got {count_num}")
        if start_num + count_num - 1 > total:
            raise ValueError(f"Range {start_num} to {start_num + count_num - 1} exceeds available recordings count {total}")

        return start_num, count_num

    # Format 3: Single number (e.g. "5" -> download only file 5)
    if cleaned.isdigit():
        single_num = int(cleaned)
        if single_num < 1 or single_num > total:
            raise ValueError(f"Recording index {single_num} out of bounds (1..{total})")
        return single_num, 1

    raise ValueError(f"Invalid range specification '{range_str}'. Examples: 'all', '1-10', '1 10'")


def resolve_camera(cameras: dict[CameraNumber, Camera], camera_spec: str | int) -> Camera:
    """Resolve camera entity by number, display name, or short name."""
    # Attempt 1: Match by integer channel number
    try:
        num = int(camera_spec)
        camera_num = CameraNumber(num)
        if camera_num in cameras:
            return cameras[camera_num]
    except ValueError, TypeError:
        pass

    # Attempt 2: Match by name or display name (case-insensitive)
    spec_str = str(camera_spec).strip().lower()
    for cam in cameras.values():
        if cam.name.lower() == spec_str:
            return cam
        if cam.display_name.lower() == spec_str:
            return cam
        if cam.archive_name.lower() == spec_str:
            return cam

    available_list = ", ".join(f"{int(num)}: {cam.name}" for num, cam in sorted(cameras.items()))
    raise ValueError(f"Camera '{camera_spec}' not found. Available cameras: [{available_list}]")


def discover_dates(session: requests.Session, host: str) -> dict[tuple[int, int], list[RecordingDate]]:
    """Discover and display available recording dates from the NVR."""
    print()
    print("Checking available recording dates...")

    try:
        months, discovery_duration = discover_available_dates(
            session=session,
            host=host,
            discovery_track_id=TrackId(DATE_DISCOVERY_TRACK_ID),
            timeout=TIMEOUT,
        )
    except (requests.RequestException, ET.ParseError, RuntimeError, ValueError) as exc:
        print()
        display_error(f"DATE SEARCH FAILED: {exc}")
        sys.exit(1)

    display_available_dates(months)
    print(f"Date availability search completed in {format_duration(discovery_duration)}.")

    return months


def search_recordings_for_date(
    session: requests.Session,
    host: str,
    camera: Camera,
    stream: str | StreamType,
    recording_date: date,
    quiet: bool = False,
) -> tuple[Sequence[Recording], float]:
    """Search the NVR for all recordings matching the selected date and track."""
    track_id = camera.track_id(stream)
    stream_display = str(stream).replace("streamtype.", "").capitalize()

    if not quiet:
        print()
        print("=" * 70)
        print("SEARCHING RECORDINGS")
        print("=" * 70)
        print(f"Date:      {recording_date.isoformat()}")
        print(f"Camera:    [{int(camera.number)}] {camera.name}")
        print(f"Stream:    {stream_display}")
        print(f"Track ID:  {int(track_id)}")
        print()

    started = time.monotonic()

    recordings = get_all_recordings(
        session=session,
        host=host,
        track_id=track_id,
        recording_date=recording_date,
        batch_size=BATCH_SIZE,
        timeout=TIMEOUT,
    )

    duration = time.monotonic() - started

    if not recordings:
        if not quiet:
            print(f"No recordings found. Search completed in {format_duration(duration)}.")
        return [], duration

    total_size = recording_total_size(recordings)

    if not quiet:
        print(f"Found {len(recordings)} recordings in {format_duration(duration)}.")
        print(f"Total reported size: {int(total_size) / (1024 * 1024 * 1024):.2f} GB")

    return recordings, duration


def setup_signal_handler(cancel_event: threading.Event) -> None:
    """Register signal handlers for SIGINT to ensure graceful interruption and cleanup."""

    def sigint_handler(signum: int, frame: FrameType | None) -> None:
        if not cancel_event.is_set():
            cancel_event.set()
            display_abort_notice()
        else:
            # If pressed again, force exit
            sys.exit(130)

    signal.signal(signal.SIGINT, sigint_handler)


def run_app(argv: Sequence[str] | None = None) -> int:
    """Main CLI execution flow supporting both headless flags and interactive fallback."""
    cancel_event = threading.Event()
    setup_signal_handler(cancel_event)

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        # --------------------------------------------------------
        # 1. Host & Port Configuration
        # --------------------------------------------------------
        effective_host = args.host or NVR_HOST
        if not effective_host:
            display_error("NVR host is not configured. Specify --host or set HIKVISION_HOST in .env")
            return 1

        effective_port = args.port or NVR_PORT or 80
        effective_workers = max(1, min(args.workers or NVR_MAX_WORKERS or 2, 4))
        host_endpoint = format_host_port(effective_host, effective_port)

        # --------------------------------------------------------
        # 2. Authentication Resolution & Session Creation
        # --------------------------------------------------------
        effective_username = args.username or NVR_USERNAME
        effective_password = args.password or NVR_PASSWORD
        effective_auth_type = (args.auth_type or NVR_AUTH_TYPE or "digest").lower()

        if not effective_username:
            if args.non_interactive:
                display_error("Authentication credentials missing. Specify --username/--password or configure .env")
                return 1
            print()
            print("Hikvision NVR Authentication")
            print("=" * 40)
            username_input = input("Enter NVR Username: ").strip()
            password_input = getpass.getpass("Enter NVR Password: ").strip()
            if not username_input or not password_input:
                display_error("Username and password are required.")
                return 1
            effective_username = username_input
            effective_password = password_input

        elif not effective_password:
            if args.non_interactive:
                display_error("Password is required when username is provided.")
                return 1
            password_input = getpass.getpass(f"Enter NVR Password for {effective_username}: ").strip()
            if not password_input:
                display_error("Password is required.")
                return 1
            effective_password = password_input

        try:
            session = create_authenticated_session(
                host=effective_host,
                port=effective_port,
                username=effective_username,
                password=SecretStr(effective_password),
                auth_type=effective_auth_type,
            )
        except (RuntimeError, ValueError) as exc:
            display_error(f"AUTHENTICATION SETUP FAILED: {exc}")
            return 1

        display_header(effective_host, port=effective_port, username=effective_username)

        # --------------------------------------------------------
        # 3. Dynamic Camera Discovery
        # --------------------------------------------------------
        discovery_service = CameraDiscoveryService()
        try:
            cameras = discovery_service.get_cameras(
                session=session,
                host=effective_host,
                port=effective_port,
                config_file=CAMERA_CONFIG if CAMERA_CONFIG.exists() else None,
                force_refresh=args.refresh_cameras,
                timeout=TIMEOUT,
            )
        except (requests.RequestException, ET.ParseError, RuntimeError, ValueError, FileNotFoundError) as exc:
            display_error(f"CAMERA DISCOVERY FAILED: {exc}")
            return 1

        # --------------------------------------------------------
        # 4. Date Selection (Headless vs Interactive)
        # --------------------------------------------------------
        recording_date: date | None = None
        if args.date:
            try:
                recording_date = parse_date_spec(args.date)
            except ValueError as exc:
                display_error(str(exc))
                return 1
        elif args.non_interactive:
            display_error("--date is required when running in --non-interactive mode.")
            return 1
        else:
            months = discover_dates(session, host_endpoint)
            recording_date = ask_recording_date(months)
            if recording_date is None:
                print("Cancelled.")
                return 0

        # --------------------------------------------------------
        # 5. Camera Selection (Headless vs Interactive)
        # --------------------------------------------------------
        camera: Camera | None = None
        if args.camera:
            try:
                camera = resolve_camera(cameras, args.camera)
            except ValueError as exc:
                display_error(str(exc))
                return 1
        elif args.non_interactive:
            display_error("--camera is required when running in --non-interactive mode.")
            return 1
        else:
            camera = ask_camera(cameras)
            if camera is None:
                print("Cancelled.")
                return 0

        # --------------------------------------------------------
        # 6. Stream Selection (Headless vs Interactive)
        # --------------------------------------------------------
        stream: str | StreamType | None = None
        if args.stream:
            try:
                stream = parse_stream_type(args.stream)
            except ValueError as exc:
                display_error(str(exc))
                return 1
        elif args.non_interactive:
            display_error("--stream is required when running in --non-interactive mode.")
            return 1
        else:
            stream = ask_stream(camera=camera)
            if stream is None:
                print("Cancelled.")
                return 0

        if not args.non_interactive:
            try:
                display_selection(camera, stream)
            except ValueError as exc:
                display_error(str(exc))
                return 1

        # --------------------------------------------------------
        # 7. Search Recordings
        # --------------------------------------------------------
        stream_display = str(stream).replace("streamtype.", "").capitalize()
        if args.non_interactive:
            print(f"Searching recordings for {recording_date.isoformat()} [{int(camera.number)}] {camera.name} ({stream_display})...")

        try:
            recordings, search_duration = search_recordings_for_date(
                session=session,
                host=host_endpoint,
                camera=camera,
                stream=stream,
                recording_date=recording_date,
                quiet=args.non_interactive,
            )
        except (requests.RequestException, ET.ParseError, RuntimeError, ValueError) as exc:
            display_error(f"FILE SEARCH FAILED: {exc}")
            return 1

        if not recordings:
            if args.non_interactive:
                print(f"No recordings found for {recording_date.isoformat()} ({format_duration(search_duration)}).")
            return 0

        # --------------------------------------------------------
        # 8. Save and Display Recording List
        # --------------------------------------------------------
        track_id = camera.track_id(stream)
        stream_name = camera.stream_name(stream)
        destination_dir: Path = (
            args.output_dir if args.output_dir is not None else OUTPUT_ROOT / f"{recording_date:%Y%m%d}_{camera.archive_name}_{stream_name}"
        )

        list_file = save_recording_list(
            recordings=recordings,
            output_dir=destination_dir,
            camera_number=camera.number,
            camera_name=camera.name,
            stream_name=stream_name,
            recording_date=recording_date,
        )
        total_size = recording_total_size(recordings)
        total_gb = int(total_size) / (1024 * 1024 * 1024)

        if args.non_interactive:
            print(f"Found {len(recordings)} recordings ({total_gb:.2f} GB) in {format_duration(search_duration)}.")
            print(f"Recording list saved to: {list_file}\n")
        else:
            print(f"Recording list saved to: {list_file}")
            display_recording_list(recordings)

        # --------------------------------------------------------
        # 9. Range Selection (Headless vs Interactive)
        # --------------------------------------------------------
        selection: tuple[int, int] | None = None
        if args.range:
            try:
                selection = parse_range_spec(args.range, len(recordings))
            except ValueError as exc:
                display_error(str(exc))
                return 1
        elif args.non_interactive:
            # Default to downloading all files in headless mode
            selection = (1, len(recordings))
        else:
            selection = ask_download_selection(len(recordings))
            if selection is None:
                print("Nothing downloaded.")
                return 0

            start_idx, count_num = selection
            if not confirm_download(
                camera=camera,
                stream=stream,
                recording_date=recording_date,
                recordings=recordings,
                start=start_idx,
                count=count_num,
            ):
                print("Cancelled.")
                return 0

        start, count = selection

        # --------------------------------------------------------
        # 10. Execute Concurrent Download Pool with Interruption Handling
        # --------------------------------------------------------
        download_res = download_recordings_concurrent(
            session=session,
            host=effective_host,
            recordings=recordings,
            track_id=track_id,
            output_dir=destination_dir,
            start=start,
            count=count,
            max_workers=effective_workers,
            port=effective_port,
            timeout=TIMEOUT,
            progress_callback=display_download_progress,
            cancel_event=cancel_event,
        )

        if cancel_event.is_set():
            return 130

        if not download_res.success:
            print()
            print("=" * 70)
            print("DOWNLOAD STOPPED")
            print("=" * 70)
            print(f"Failed recording: {download_res.failed_index}")
            if download_res.error_message:
                print(f"Reason: {download_res.error_message}")
            print("Fix the problem and run the script again.")
            print("Existing complete files will be skipped.")
            return 1

        # --------------------------------------------------------
        # 11. Summary Display
        # --------------------------------------------------------
        display_download_summary(
            camera=camera,
            stream=stream,
            recording_date=recording_date,
            track_id=track_id,
            selection=selection,
            search_duration=search_duration,
            result=download_res,
            recordings=recordings,
            output_dir=destination_dir,
        )
        return 0

    except KeyboardInterrupt:
        if not cancel_event.is_set():
            cancel_event.set()
            display_abort_notice()
        return 130
    except (RuntimeError, ValueError, OSError, requests.RequestException) as exc:
        display_error(f"EXECUTION ERROR: {exc}")
        return 1


def main() -> None:
    """Console script entry point."""
    exit_code = run_app(sys.argv[1:])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
