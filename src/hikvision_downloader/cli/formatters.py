import sys
import threading
from collections.abc import Sequence
from datetime import date
from pathlib import Path

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

_progress_lock = threading.Lock()


def display_header(host: str | None, port: int = 80, username: str | None = None) -> None:
    """Display the application header."""
    host_display = f"{host}:{port}" if host and port != 80 else (host or "Not configured")
    user_display = f" (user: {username})" if username else ""

    print()
    print("Hikvision Recording Downloader")
    print("=" * 40)
    print(f"NVR: {host_display}{user_display}")


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

    for number, camera in sorted(cameras.items()):
        print(f"{int(number):>3}. [{int(number):>2}] {camera.name:<18} {camera.ip_address}")

    print("=" * 60)


def display_selection(camera: Camera, stream: str | StreamType) -> None:
    """Display the selected camera and stream parameters."""
    track_id = camera.track_id(stream)
    stream_display = str(stream).replace("streamtype.", "").capitalize()

    print()
    print(f"Camera:    [{int(camera.number)}] {camera.name}")
    print(f"Camera IP: {camera.ip_address}")
    print(f"Stream:    {stream_display}")
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


def format_time_span(start: str | None, end: str | None) -> str:
    """Format start and end ISO timestamps into a compact range string '(HH:MM:SS - HH:MM:SS)'."""
    if not start or not end:
        return ""

    s_clean = start.rstrip("Z").replace("T", " ").strip()
    e_clean = end.rstrip("Z").replace("T", " ").strip()

    s_time = s_clean.split(" ")[-1][:8]
    e_time = e_clean.split(" ")[-1][:8]

    if not s_time or not e_time:
        return ""

    return f"({s_time} - {e_time})"


def render_progress_bar(pct: float, length: int = 12) -> str:
    """Render a visual ASCII progress bar [██████░░░░]."""
    clamped = min(1.0, max(0.0, pct))
    filled = int(length * clamped)
    return f"[{'█' * filled}{'░' * (length - filled)}]"


class MultiProgressDisplay:
    """Thread-safe terminal progress manager supporting concurrent multi-line download streams."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_lines: dict[int, str] = {}
        self._rendered_count = 0

    def update(self, progress: DownloadProgress) -> None:
        """Process incoming progress update and render to terminal."""
        size_mb = float(progress.bytes_downloaded) / (1024 * 1024)
        time_span = format_time_span(progress.start_time, progress.end_time)
        time_str = f"  {time_span}" if time_span else ""
        is_tty = sys.stdout.isatty()

        with self._lock:
            idx = progress.current_index

            if progress.is_skipped:
                if idx in self._active_lines:
                    del self._active_lines[idx]

                line = f"[{progress.current_index}/{progress.total_files}] {progress.filename}{time_str}  {size_mb:.2f} MB  SKIP"
                self._finalize_line(line, is_tty)

            elif progress.is_completed:
                if idx in self._active_lines:
                    del self._active_lines[idx]

                duration_str = format_duration(progress.elapsed_seconds)
                line = f"[{progress.current_index}/{progress.total_files}] {progress.filename}{time_str}  {size_mb:.2f} MB  {duration_str}  OK"
                self._finalize_line(line, is_tty)

            else:
                # Active in-flight transfer update
                total_mb = float(progress.file_size_bytes) / (1024 * 1024) if progress.file_size_bytes > 0 else size_mb
                pct = (float(progress.bytes_downloaded) / float(progress.file_size_bytes)) if progress.file_size_bytes > 0 else 0.0
                pct_str = f"{pct * 100:>5.1f}%"
                bar = render_progress_bar(pct, length=12)
                speed_str = f"{float(progress.speed_mbps):>5.1f} Mbps" if float(progress.speed_mbps) > 0 else "-- Mbps"

                # ETA calculation
                if float(progress.speed_mbps) > 0 and progress.file_size_bytes > progress.bytes_downloaded:
                    rem_bytes = int(progress.file_size_bytes) - int(progress.bytes_downloaded)
                    speed_bytes_sec = float(progress.speed_mbps) * 1_000_000.0 / 8.0
                    eta_sec = rem_bytes / speed_bytes_sec if speed_bytes_sec > 0 else 0
                    eta_str = f"ETA: {format_duration(eta_sec)}"
                else:
                    eta_str = "ETA: --"

                line = f"[{progress.current_index}/{progress.total_files}] {progress.filename}{time_str}  {bar} {pct_str}  {size_mb:>6.2f}/{total_mb:>6.2f} MB  {speed_str}  {eta_str}"
                self._active_lines[idx] = line

                if is_tty:
                    self._render_active_lines()
                else:
                    # If non-TTY and just starting (0 bytes), print starting notification so log is not silent
                    if int(progress.bytes_downloaded) == 0:
                        print(
                            f"[{progress.current_index}/{progress.total_files}] Downloading {progress.filename}{time_str} ({total_mb:.2f} MB)...",
                            flush=True,
                        )

    def _finalize_line(self, line: str, is_tty: bool) -> None:
        """Print a completed/skipped permanent line, redrawing any remaining active lines below it."""
        if not is_tty:
            print(line, flush=True)
            return

        # Move cursor up to the top of previously rendered active block and clear downward
        if self._rendered_count > 0:
            sys.stdout.write(f"\033[{self._rendered_count}A\r\033[J")

        # Print the finalized line permanently with newline
        sys.stdout.write(f"{line}\033[K\n")

        # Redraw remaining active lines below this completed line
        self._rendered_count = 0
        if self._active_lines:
            for active_idx in sorted(self._active_lines.keys()):
                sys.stdout.write(f"{self._active_lines[active_idx]}\033[K\n")
            self._rendered_count = len(self._active_lines)

        sys.stdout.flush()

    def _render_active_lines(self) -> None:
        """Redraw all current active in-flight lines in terminal in sorted order."""
        if self._rendered_count > 0:
            sys.stdout.write(f"\033[{self._rendered_count}A\r")

        for active_idx in sorted(self._active_lines.keys()):
            sys.stdout.write(f"{self._active_lines[active_idx]}\033[K\n")

        self._rendered_count = len(self._active_lines)
        sys.stdout.flush()

    def reset(self) -> None:
        """Reset internal active tracker state."""
        with self._lock:
            self._active_lines.clear()
            self._rendered_count = 0


_progress_display = MultiProgressDisplay()


def reset_progress_display() -> None:
    """Reset terminal progress display state."""
    _progress_display.reset()


def display_download_progress(progress: DownloadProgress) -> None:
    """Render download progress to the terminal with in-place multi-line concurrent updates."""
    _progress_display.update(progress)


def display_download_summary(
    camera: Camera,
    stream: str | StreamType,
    recording_date: date,
    track_id: TrackId,
    selection: tuple[int, int],
    search_duration: float,
    result: DownloadResult,
    recordings: Sequence[Recording] | None = None,
    output_dir: Path | None = None,
) -> None:
    """Display final batch transfer statistics and averages."""
    start, count = selection
    downloaded_bytes = int(result.downloaded_bytes)
    total_download_time = result.total_duration_seconds
    stream_display = str(stream).replace("streamtype.", "").capitalize()

    print()
    print("=" * 70)
    print("DOWNLOAD BATCH COMPLETE")
    print("=" * 70)
    print(f"Camera:          [{int(camera.number)}] {camera.name}")
    print(f"Stream:          {stream_display} ({int(track_id)})")
    print(f"Date:            {recording_date.isoformat()}")
    if recordings and 1 <= start <= len(recordings):
        first_rec = recordings[start - 1]
        last_rec = recordings[min(start + count - 1, len(recordings)) - 1]
        start_ts = first_rec.start[:19].replace("T", " ")
        end_ts = last_rec.end[:19].replace("T", " ")
        print(f"Time span:       {start_ts} -> {end_ts}")
    print(f"Recordings:      {start}-{start + count - 1}")
    print(f"Downloaded:      {result.downloaded_files}")
    print(f"Skipped:         {result.skipped_files}")
    print(f"Files size:      {downloaded_bytes / (1024 * 1024 * 1024):.2f} GB")
    if output_dir is not None:
        print(f"Output folder:   {output_dir}")
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
