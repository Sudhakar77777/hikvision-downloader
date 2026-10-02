from collections.abc import Sequence
from datetime import date

from ..core.models import Camera, CameraNumber, Recording, RecordingDate, StreamType
from .formatters import display_camera_list


def ask_camera(cameras: dict[CameraNumber, Camera]) -> Camera | None:
    """Prompt the user to select a camera from the available camera list."""
    display_camera_list(cameras)

    while True:
        value = input("Select camera (q to quit): ").strip()

        if value.lower() == "q":
            return None

        try:
            num = int(value)
            camera_number = CameraNumber(num)

            if camera_number not in cameras:
                raise ValueError

            return cameras[camera_number]

        except ValueError:
            print(f"Please enter a valid camera number from the list (1 to {len(cameras)}).")


def ask_stream() -> StreamType | None:
    """Prompt the user to select Main or Sub stream."""
    print()
    print("Stream")
    print("=" * 30)
    print("1. Main")
    print("2. Sub")
    print("=" * 30)

    while True:
        value = input("Select stream (q to quit): ").strip().lower()

        if value == "q":
            return None

        if value == "1":
            return StreamType.MAIN

        if value == "2":
            return StreamType.SUB

        print("Please enter 1 for Main or 2 for Sub.")


def ask_recording_date(months: dict[tuple[int, int], list[RecordingDate]]) -> date | None:
    """Prompt the user to select one of the discovered recording dates."""
    available_dates = {item.iso for dates in months.values() for item in dates}

    while True:
        value = input("Select date [YYYY-MM-DD] (q to quit): ").strip()

        if value.lower() == "q":
            return None

        try:
            selected = date.fromisoformat(value)
        except ValueError:
            print("Please enter a valid date in YYYY-MM-DD format.")
            continue

        if selected.isoformat() not in available_dates:
            print("No recording was reported for that date. Please choose a listed date.")
            continue

        return selected


def ask_download_selection(total: int) -> tuple[int, int] | None:
    """Prompt the user to download all files or specify a START COUNT range."""
    print(f"Download all {total} files? [Y/n]")

    value = input().strip().lower()

    if value in ("", "y", "yes"):
        return 1, total

    if value not in ("n", "no"):
        print("Please answer yes or no.")
        return ask_download_selection(total)

    print()
    print("Enter: START COUNT")
    print("Examples:")
    print("  1 10   -> download files 1-10")
    print("  16 2   -> download files 16-17")
    print("  1 97   -> download files 1-97")
    print()

    while True:
        raw_val = input("Selection (q to quit): ").strip()

        if raw_val.lower() == "q":
            return None

        try:
            parts = raw_val.split()

            if len(parts) != 2:
                raise ValueError

            start = int(parts[0])
            count = int(parts[1])

            if start < 1 or count < 1:
                raise ValueError

            end = start + count - 1

            if end > total:
                print(f"ERROR: last file would be {end}, but only {total} exist.")
                continue

            return start, count

        except ValueError:
            print("Please enter two positive numbers separated by a space, for example: 1 10")


def confirm_download(
    camera: Camera,
    stream: StreamType,
    recording_date: date,
    recordings: Sequence[Recording],
    start: int,
    count: int,
) -> bool:
    """Confirm the selected download batch with summary details."""
    track_id = camera.track_id(stream)
    end = start + count - 1

    print()
    print("=" * 70)
    print("DOWNLOAD SELECTION")
    print("=" * 70)
    print(f"Camera:      [{int(camera.number)}] {camera.name}")
    print(f"Stream:      {stream.capitalize()} ({int(track_id)})")
    print(f"Date:        {recording_date.isoformat()}")
    print(f"Recordings:  {start}-{end}")
    print(f"Files:       {count}")
    print()

    selected_size = sum(int(recording.size_bytes) for recording in recordings[start - 1 : start - 1 + count])

    print(f"Reported size: {selected_size / (1024 * 1024 * 1024):.2f} GB")

    answer = input("Continue? [Y/n]: ").strip().lower()

    return answer in ("", "y", "yes")
