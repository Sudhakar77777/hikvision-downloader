#!/usr/bin/env python3

import sys
import time
from collections.abc import Sequence
from datetime import date
from xml.etree import ElementTree as ET

import requests

from .cli.formatters import (
    display_available_dates,
    display_download_progress,
    display_download_summary,
    display_header,
    display_recording_list,
    display_selection,
)
from .cli.interactive import (
    ask_camera,
    ask_download_selection,
    ask_recording_date,
    ask_stream,
    confirm_download,
)
from .config import (
    BATCH_SIZE,
    CAMERA_CONFIG,
    DATE_DISCOVERY_TRACK_ID,
    NVR_HOST,
    OUTPUT_ROOT,
    TIMEOUT,
)
from .core.cameras import load_cameras
from .core.dates import discover_available_dates
from .core.downloads import download_recordings, format_duration
from .core.models import Camera, Recording, RecordingDate, StreamType
from .core.recordings import get_all_recordings, recording_total_size, save_recording_list
from .http_client import make_session

# ============================================================
# Application Orchestration
# ============================================================


def discover_dates(session: requests.Session, host: str) -> dict[tuple[int, int], list[RecordingDate]]:
    """Discover and display dates with available recordings."""
    print()
    print("Checking available recording dates...")

    try:
        months, discovery_duration = discover_available_dates(
            session=session,
            host=host,
            discovery_track_id=DATE_DISCOVERY_TRACK_ID,
            timeout=TIMEOUT,
        )
    except (requests.RequestException, ET.ParseError, RuntimeError, ValueError) as exc:
        print()
        print("DATE SEARCH FAILED")
        print(exc)
        sys.exit(1)

    display_available_dates(months)
    print(f"Date availability search completed in {format_duration(discovery_duration)}.")

    return months


def search_recordings_for_date(
    session: requests.Session,
    host: str,
    camera: Camera,
    stream: StreamType,
    recording_date: date,
) -> tuple[Sequence[Recording], float] | None:
    """Search the NVR for all recordings matching the selected date and track."""
    track_id = camera.track_id(stream)

    print()
    print("=" * 70)
    print("SEARCHING RECORDINGS")
    print("=" * 70)
    print(f"Date:      {recording_date.isoformat()}")
    print(f"Camera:    [{int(camera.number)}] {camera.name}")
    print(f"Stream:    {stream.capitalize()}")
    print(f"Track ID:  {int(track_id)}")
    print()

    started = time.monotonic()

    try:
        recordings = get_all_recordings(
            session=session,
            host=host,
            track_id=track_id,
            recording_date=recording_date,
            batch_size=BATCH_SIZE,
            timeout=TIMEOUT,
        )
    except (requests.RequestException, ET.ParseError, RuntimeError, ValueError) as exc:
        print()
        print("FILE SEARCH FAILED")
        print(exc)
        sys.exit(1)

    duration = time.monotonic() - started

    if not recordings:
        print(f"No recordings found. Search completed in {format_duration(duration)}.")
        return None

    total_size = recording_total_size(recordings)

    print(f"Found {len(recordings)} recordings in {format_duration(duration)}.")
    print(f"Total reported size: {int(total_size) / (1024 * 1024 * 1024):.2f} GB")

    return recordings, duration


def main() -> None:
    """Run the complete interactive downloader workflow."""
    if not NVR_HOST:
        print("ERROR: HIKVISION_HOST is not configured in .env")
        sys.exit(1)

    display_header(NVR_HOST)
    cameras = load_cameras(CAMERA_CONFIG)
    session = make_session()

    # --------------------------------------------------------
    # Date availability
    # --------------------------------------------------------
    months = discover_dates(session, NVR_HOST)

    recording_date = ask_recording_date(months)
    if recording_date is None:
        print("Cancelled.")
        return

    # --------------------------------------------------------
    # Camera and stream
    # --------------------------------------------------------
    camera = ask_camera(cameras)
    if camera is None:
        print("Cancelled.")
        return

    stream = ask_stream()
    if stream is None:
        print("Cancelled.")
        return

    display_selection(camera, stream)

    # --------------------------------------------------------
    # Search recordings
    # --------------------------------------------------------
    result = search_recordings_for_date(
        session=session,
        host=NVR_HOST,
        camera=camera,
        stream=stream,
        recording_date=recording_date,
    )

    if result is None:
        return

    recordings, search_duration = result

    # --------------------------------------------------------
    # Save and display recording list
    # --------------------------------------------------------
    track_id = camera.track_id(stream)
    stream_name = camera.stream_name(stream)
    output_dir = OUTPUT_ROOT / f"{recording_date:%Y%m%d}_{camera.archive_name}_{stream_name}"

    list_file = save_recording_list(
        recordings=recordings,
        output_dir=output_dir,
        camera_number=camera.number,
        camera_name=camera.name,
        stream_name=stream_name,
        recording_date=recording_date,
    )
    print(f"Recording list saved to: {list_file}")

    display_recording_list(recordings)

    # --------------------------------------------------------
    # Download selection
    # --------------------------------------------------------
    selection = ask_download_selection(len(recordings))
    if selection is None:
        print("Nothing downloaded.")
        return

    start, count = selection

    if not confirm_download(
        camera=camera,
        stream=stream,
        recording_date=recording_date,
        recordings=recordings,
        start=start,
        count=count,
    ):
        print("Cancelled.")
        return

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------
    download_res = download_recordings(
        session=session,
        host=NVR_HOST,
        recordings=recordings,
        track_id=track_id,
        output_dir=output_dir,
        start=start,
        count=count,
        timeout=TIMEOUT,
        progress_callback=display_download_progress,
    )

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
        sys.exit(1)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------
    display_download_summary(
        camera=camera,
        stream=stream,
        recording_date=recording_date,
        track_id=track_id,
        selection=selection,
        search_duration=search_duration,
        result=download_res,
    )


if __name__ == "__main__":
    main()
