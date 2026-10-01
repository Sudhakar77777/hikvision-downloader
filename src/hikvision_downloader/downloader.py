#!/usr/bin/env python3

import sys
from xml.etree import ElementTree as ET

import requests

from .cameras import ask_camera, ask_stream, display_selection, load_cameras
from .config import CAMERA_CONFIG, NVR_HOST, OUTPUT_ROOT
from .dates import ask_recording_date, discover_available_dates, display_available_dates
from .downloads import download_recordings, format_duration
from .http_client import make_session
from .recordings import ask_download_selection, display_recording_list, get_all_recordings, recording_total_size, save_recording_list

# ============================================================
# Application
# ============================================================


def display_header():
    """Display the application header."""

    print()
    print("Hikvision Recording Downloader")
    print("=" * 40)
    print(f"NVR: {NVR_HOST}")


def discover_dates(session):
    """Discover and display dates with recordings."""

    print()
    print("Checking available recording dates...")

    try:
        months, discovery_duration = discover_available_dates(session)

    except (requests.RequestException, ET.ParseError, RuntimeError, ValueError) as exc:
        print()
        print("DATE SEARCH FAILED")
        print(exc)
        sys.exit(1)

    display_available_dates(months)

    print(f"Date availability search completed in {format_duration(discovery_duration)}.")

    return months


def search_recordings_for_date(session, camera, stream, recording_date):
    """Search the NVR for all recordings matching the selected date and track."""

    track_id = camera.track_id(stream)

    print()
    print("=" * 70)
    print("SEARCHING RECORDINGS")
    print("=" * 70)
    print(f"Date:      {recording_date.isoformat()}")
    print(f"Camera:    [{camera.number}] {camera.name}")
    print(f"Stream:    {stream.capitalize()}")
    print(f"Track ID:  {track_id}")
    print()

    started = __import__("time").monotonic()

    try:
        recordings = get_all_recordings(session, track_id, recording_date)

    except (requests.RequestException, ET.ParseError, RuntimeError, ValueError) as exc:
        print()
        print("FILE SEARCH FAILED")
        print(exc)
        sys.exit(1)

    duration = __import__("time").monotonic() - started

    if not recordings:
        print(f"No recordings found. Search completed in {format_duration(duration)}.")
        return None

    total_size = recording_total_size(recordings)

    print(f"Found {len(recordings)} recordings in {format_duration(duration)}.")
    print(f"Total reported size: {total_size / (1024 * 1024 * 1024):.2f} GB")

    return recordings, duration


def confirm_download(camera, stream, recording_date, recordings, start, count):
    """Confirm the selected download batch."""

    track_id = camera.track_id(stream)
    end = start + count - 1

    print()
    print("=" * 70)
    print("DOWNLOAD SELECTION")
    print("=" * 70)
    print(f"Camera:      [{camera.number}] {camera.name}")
    print(f"Stream:      {stream.capitalize()} ({track_id})")
    print(f"Date:        {recording_date.isoformat()}")
    print(f"Recordings:  {start}-{end}")
    print(f"Files:       {count}")
    print()

    selected_size = recording_total_size(recordings[start - 1 : start - 1 + count])

    print(f"Reported size: {selected_size / (1024 * 1024 * 1024):.2f} GB")

    answer = input("Continue? [Y/n]: ").strip().lower()

    return answer in ("", "y", "yes")


def display_download_summary(camera, stream, recording_date, track_id, selection, search_duration, result):
    """Display the final download statistics."""

    start, count = selection

    downloaded_bytes = result["downloaded_bytes"]
    total_download_time = result["total_download_time"]

    print()
    print("=" * 70)
    print("DOWNLOAD BATCH COMPLETE")
    print("=" * 70)
    print(f"Camera:          [{camera.number}] {camera.name}")
    print(f"Stream:          {stream.capitalize()} ({track_id})")
    print(f"Date:            {recording_date.isoformat()}")
    print(f"Recordings:      {start}-{start + count - 1}")
    print(f"Downloaded:      {result['downloaded_files']}")
    print(f"Skipped:         {result['skipped_files']}")
    print(f"Files size:      {downloaded_bytes / (1024 * 1024 * 1024):.2f} GB")
    print(f"Search time:     {format_duration(search_duration)}")
    print(f"Download time:   {format_duration(total_download_time)}")
    print(f"Total elapsed:   {format_duration(result['batch_duration'])}")

    if total_download_time > 0 and downloaded_bytes > 0:
        average_mbps = downloaded_bytes * 8 / total_download_time / 1_000_000
        print(f"Average speed:   {average_mbps:.2f} Mbps")

    print("=" * 70)


def main():
    """Run the complete interactive downloader workflow."""

    display_header()
    cameras = load_cameras(CAMERA_CONFIG)
    session = make_session()

    # --------------------------------------------------------
    # Date availability
    # --------------------------------------------------------

    months = discover_dates(session)

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
        session,
        camera,
        stream,
        recording_date,
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

    save_recording_list(recordings, output_dir, camera.number, camera.name, stream_name, recording_date)

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
        camera,
        stream,
        recording_date,
        recordings,
        start,
        count,
    ):
        print("Cancelled.")
        return

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    result = download_recordings(
        session,
        recordings,
        track_id,
        output_dir,
        start,
        count,
    )

    if not result["success"]:
        print()
        print("=" * 70)
        print("DOWNLOAD STOPPED")
        print("=" * 70)
        print(f"Failed recording: {result['failed_number']}")
        print("Fix the problem and run the script again.")
        print("Existing complete files will be skipped.")
        sys.exit(1)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    display_download_summary(
        camera,
        stream,
        recording_date,
        track_id,
        selection,
        search_duration,
        result,
    )


if __name__ == "__main__":
    main()
