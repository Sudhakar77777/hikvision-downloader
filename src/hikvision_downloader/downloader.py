#!/usr/bin/env python3

import sys
import time
from collections.abc import Sequence
from datetime import date
from xml.etree import ElementTree as ET

import requests

from .cli.formatters import display_available_dates
from .config import (
    BATCH_SIZE,
    DATE_DISCOVERY_TRACK_ID,
    TIMEOUT,
)
from .core.dates import discover_available_dates
from .core.downloads import format_duration
from .core.models import Camera, Recording, RecordingDate, StreamType
from .core.recordings import get_all_recordings, recording_total_size

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
    """Run the complete CLI workflow (delegates to cli.app:main)."""
    from .cli.app import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()

