import threading
import time
from collections.abc import Sequence
from pathlib import Path

import requests

from ..http_client import request_with_retry
from .models import ByteCount, DownloadProgress, DownloadResult, MegabitsPerSecond, ProgressCallback, Recording, TrackId


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable HH:MM:SS or second notation."""
    if seconds < 0:
        return "0.0s"

    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes, secs = divmod(int(seconds), 60)

    if minutes < 60:
        return f"{minutes}m {secs:02d}s"

    hours, minutes = divmod(minutes, 60)

    return f"{hours}h {minutes:02d}m {secs:02d}s"


def build_download_url(host: str, recording: Recording, track_id: TrackId) -> str:
    """Build the ISAPI download URL in the format expected by Hikvision NVR."""
    start_str = recording.start.replace("T", " ")
    end_str = recording.end.replace("T", " ")

    playback_uri = (
        f"rtsp://{host}"
        f"/Streaming/tracks/{track_id}"
        f"?starttime={start_str}"
        f"&amp;endtime={end_str}"
        f"&amp;name={recording.name}"
        f"&amp;size={int(recording.size_bytes)}"
    )

    return f"http://{host}/ISAPI/ContentMgmt/download?playbackURI={playback_uri}&onlyVerification=true"


def download_recording(
    session: requests.Session,
    host: str,
    recording: Recording,
    track_id: TrackId,
    destination: Path,
    current_index: int,
    total_files: int,
    timeout: float = 120.0,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> tuple[bool, float, ByteCount, bool, str | None]:
    """Download a single recording segment and report results."""
    if cancel_event is not None and cancel_event.is_set():
        return False, 0.0, ByteCount(0), False, "Download cancelled"

    if not recording.name or recording.name == "unknown":
        return False, 0.0, ByteCount(0), False, "Recording has invalid filename"

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        actual_size = destination.stat().st_size
        if actual_size > 0:
            if progress_callback is not None:
                progress_callback(
                    DownloadProgress(
                        current_index=current_index,
                        total_files=total_files,
                        filename=destination.name,
                        bytes_downloaded=ByteCount(actual_size),
                        file_size_bytes=ByteCount(actual_size),
                        speed_mbps=MegabitsPerSecond(0.0),
                        elapsed_seconds=0.0,
                        is_skipped=True,
                    )
                )
            return True, 0.0, ByteCount(actual_size), True, None

    url = build_download_url(host, recording, track_id)
    temp_file = destination.with_suffix(destination.suffix + ".part")
    started = time.monotonic()

    try:
        response = request_with_retry(
            session,
            "GET",
            url,
            stream=True,
            timeout=timeout,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "*/*",
                "If-Modified-Since": "0",
            },
        )

        with response, open(temp_file, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if cancel_event is not None and cancel_event.is_set():
                    temp_file.unlink(missing_ok=True)
                    return False, time.monotonic() - started, ByteCount(0), False, "Download cancelled"
                if chunk:
                    file.write(chunk)

        actual_size = temp_file.stat().st_size
        duration = time.monotonic() - started

        if actual_size == 0:
            temp_file.unlink(missing_ok=True)
            return False, duration, ByteCount(0), False, "Empty file received from NVR"

        temp_file.rename(destination)

        speed_mbps = (actual_size * 8.0 / duration / 1_000_000.0) if duration > 0 else 0.0

        if progress_callback is not None:
            progress_callback(
                DownloadProgress(
                    current_index=current_index,
                    total_files=total_files,
                    filename=destination.name,
                    bytes_downloaded=ByteCount(actual_size),
                    file_size_bytes=ByteCount(actual_size),
                    speed_mbps=MegabitsPerSecond(speed_mbps),
                    elapsed_seconds=duration,
                    is_skipped=False,
                )
            )

        return True, duration, ByteCount(actual_size), False, None

    except (OSError, ValueError, RuntimeError, requests.RequestException) as exc:
        duration = time.monotonic() - started
        temp_file.unlink(missing_ok=True)
        return False, duration, ByteCount(0), False, str(exc)


def download_recordings(
    session: requests.Session,
    host: str,
    recordings: Sequence[Recording],
    track_id: TrackId,
    output_dir: Path,
    start: int,
    count: int,
    timeout: float = 120.0,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> DownloadResult:
    """Download a slice of recordings and return aggregate statistics."""
    total_recordings = len(recordings)
    if start < 1 or start > total_recordings:
        raise ValueError(f"Start index {start} out of bounds (1..{total_recordings})")
    if count < 1:
        raise ValueError(f"Count must be >= 1, got {count}")
    if start + count - 1 > total_recordings:
        raise ValueError(f"Range {start}..{start + count - 1} exceeds total recordings {total_recordings}")

    selected = recordings[start - 1 : start - 1 + count]
    batch_started = time.monotonic()
    downloaded_files = 0
    skipped_files = 0
    downloaded_bytes = 0

    for offset, recording in enumerate(selected, start=start):
        if cancel_event is not None and cancel_event.is_set():
            return DownloadResult(
                success=False,
                total_files=count,
                downloaded_files=downloaded_files,
                skipped_files=skipped_files,
                downloaded_bytes=ByteCount(downloaded_bytes),
                total_duration_seconds=time.monotonic() - batch_started,
                failed_index=offset,
                error_message="Batch download cancelled by user",
            )

        filename = f"{offset}_{recording.name}" if recording.name.endswith(".mp4") else f"{offset}_{recording.name}.mp4"
        destination = output_dir / filename

        success, _duration, actual_size, is_skipped, error_msg = download_recording(
            session=session,
            host=host,
            recording=recording,
            track_id=track_id,
            destination=destination,
            current_index=offset,
            total_files=total_recordings,
            timeout=timeout,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
        )

        if not success:
            return DownloadResult(
                success=False,
                total_files=count,
                downloaded_files=downloaded_files,
                skipped_files=skipped_files,
                downloaded_bytes=ByteCount(downloaded_bytes),
                total_duration_seconds=time.monotonic() - batch_started,
                failed_index=offset,
                error_message=error_msg,
            )

        if is_skipped:
            skipped_files += 1
        else:
            downloaded_files += 1
            downloaded_bytes += int(actual_size)

    return DownloadResult(
        success=True,
        total_files=count,
        downloaded_files=downloaded_files,
        skipped_files=skipped_files,
        downloaded_bytes=ByteCount(downloaded_bytes),
        total_duration_seconds=time.monotonic() - batch_started,
        failed_index=None,
        error_message=None,
    )
