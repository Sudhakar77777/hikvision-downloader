from collections.abc import Sequence
from datetime import date

from ..core.downloads import format_duration
from ..core.models import (
    Camera,
    CameraNumber,
    DownloadProgress,
    DownloadResult,
    Recording,
    RecordingDate,
    StreamType,
    TrackId,
)


def display_header(host: str | None) -> None:
    """Display the application header."""
    print()
    print("Hikvision Recording Downloader")
    print("=" * 40)
    print(f"NVR: {host or 'Not configured'}")


def display_available_dates(months: dict[tuple[int, int], list[RecordingDate]]) -> None:
    """Display available recording dates grouped by calendar month."""
    print()
    print("Available recording dates")
    print("=========================")

    for (year, month), dates in sorted(months.items(), reverse=True):
        recorded_days = sorted(item.day for item in dates)

        print()
        print(f"{year:04d}-{month:02d}")

        if not recorded_days:
            print("  No recordings")
            continue

        for start in range(0, len(recorded_days), 10):
            row = recorded_days[start : start + 10]
            print("  " + "  ".join(f"{day:02d}" for day in row))

    print()


def display_camera_list(cameras: dict[CameraNumber, Camera]) -> None:
    """Display available cameras in a formatted table."""
    print()
    print("Cameras")
    print("=" * 60)

    for number, camera in cameras.items():
        print(f"{int(number):>3}. [{int(number):>2}] {camera.name:<18} {camera.ip_address}")

    print("=" * 60)


def display_selection(camera: Camera, stream: StreamType) -> None:
    """Display the selected camera and stream parameters."""
    track_id = camera.track_id(stream)

    print()
    print(f"Camera:    [{int(camera.number)}] {camera.name}")
    print(f"Camera IP: {camera.ip_address}")
    print(f"Stream:    {stream.capitalize()}")
    print(f"Track ID:  {int(track_id)}")


def display_recording_list(recordings: Sequence[Recording]) -> None:
    """Display a numbered table of available recordings with sizes and times."""
    print()
    print("=" * 110)
    print(f"{'#':>4}  {'Start':19}  {'End':19}  {'Size (MB)':>10}  Name")
    print("=" * 110)

    total_bytes = sum(int(recording.size_bytes) for recording in recordings)

    for number, recording in enumerate(recordings, start=1):
        size_mb = float(recording.size_bytes) / (1024 * 1024)
        print(f"{number:>4}  {recording.start[:19]}  {recording.end[:19]}  {size_mb:10.1f}  {recording.name}")

    print("=" * 110)
    print(f"Total: {len(recordings)} recordings  |  {total_bytes / (1024 * 1024 * 1024):.2f} GB")
    print()


def display_download_progress(progress: DownloadProgress) -> None:
    """Render a single download progress line to the terminal."""
    size_mb = float(progress.bytes_downloaded) / (1024 * 1024)

    if progress.is_skipped:
        print(f"[{progress.current_index}/{progress.total_files}] {progress.filename}  {size_mb:.2f} MB  SKIP")
    else:
        duration_str = format_duration(progress.elapsed_seconds)
        print(f"[{progress.current_index}/{progress.total_files}] {progress.filename}  {size_mb:.2f} MB  {duration_str}  OK")


def display_download_summary(
    camera: Camera,
    stream: StreamType,
    recording_date: date,
    track_id: TrackId,
    selection: tuple[int, int],
    search_duration: float,
    result: DownloadResult,
) -> None:
    """Display final batch transfer statistics and averages."""
    start, count = selection
    downloaded_bytes = int(result.downloaded_bytes)
    total_download_time = result.total_duration_seconds

    print()
    print("=" * 70)
    print("DOWNLOAD BATCH COMPLETE")
    print("=" * 70)
    print(f"Camera:          [{int(camera.number)}] {camera.name}")
    print(f"Stream:          {stream.capitalize()} ({int(track_id)})")
    print(f"Date:            {recording_date.isoformat()}")
    print(f"Recordings:      {start}-{start + count - 1}")
    print(f"Downloaded:      {result.downloaded_files}")
    print(f"Skipped:         {result.skipped_files}")
    print(f"Files size:      {downloaded_bytes / (1024 * 1024 * 1024):.2f} GB")
    print(f"Search time:     {format_duration(search_duration)}")
    print(f"Download time:   {format_duration(total_download_time)}")
    print(f"Total elapsed:   {format_duration(result.total_duration_seconds)}")

    if total_download_time > 0 and downloaded_bytes > 0:
        average_mbps = downloaded_bytes * 8.0 / total_download_time / 1_000_000.0
        print(f"Average speed:   {average_mbps:.2f} Mbps")

    print("=" * 70)


def display_abort_notice() -> None:
    """Display a notification banner when execution is cancelled by user."""
    print()
    print("=" * 70)
    print("[ABORTED] Operation cancelled by user (Ctrl+C).")
    print("Cleaning up temporary download files...")
    print("=" * 70)


def display_error(message: str) -> None:
    """Display a formatted error message banner."""
    print()
    print("=" * 70)
    print(f"ERROR: {message}")
    print("=" * 70)

