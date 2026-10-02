import threading
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def build_download_url(host: str, recording: Recording, track_id: TrackId, port: int = 80) -> str:
    """Build the ISAPI download URL in the format expected by Hikvision NVR."""
    if recording.playback_uri and f"tracks/{track_id}" in recording.playback_uri:
        playback_uri = recording.playback_uri
    else:
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

    host_str = host if (":" in host or port == 80) else f"{host}:{port}"

    return f"http://{host_str}/ISAPI/ContentMgmt/download?playbackURI={playback_uri}&onlyVerification=true"


def download_recording(
    session: requests.Session,
    host: str,
    recording: Recording,
    track_id: TrackId,
    destination: Path,
    current_index: int,
    total_files: int,
    port: int = 80,
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
                        is_completed=True,
                        start_time=str(recording.start),
                        end_time=str(recording.end),
                    )
                )
            return True, 0.0, ByteCount(actual_size), True, None

    target_bytes = int(recording.size_bytes)
    if progress_callback is not None:
        progress_callback(
            DownloadProgress(
                current_index=current_index,
                total_files=total_files,
                filename=destination.name,
                bytes_downloaded=ByteCount(0),
                file_size_bytes=ByteCount(target_bytes),
                speed_mbps=MegabitsPerSecond(0.0),
                elapsed_seconds=0.0,
                is_skipped=False,
                is_completed=False,
                start_time=str(recording.start),
                end_time=str(recording.end),
            )
        )

    url = build_download_url(host, recording, track_id, port=port)
    temp_file = destination.with_suffix(destination.suffix + ".part")
    started = time.monotonic()
    last_emit_time = started
    downloaded_bytes = 0

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
            for chunk in response.iter_content(chunk_size=256 * 1024):
                if cancel_event is not None and cancel_event.is_set():
                    temp_file.unlink(missing_ok=True)
                    return False, time.monotonic() - started, ByteCount(0), False, "Download cancelled"
                if chunk:
                    file.write(chunk)
                    downloaded_bytes += len(chunk)
                    now = time.monotonic()
                    if progress_callback is not None and (now - last_emit_time >= 0.25):
                        elapsed = now - started
                        speed_mbps = (downloaded_bytes * 8.0 / elapsed / 1_000_000.0) if elapsed > 0 else 0.0
                        progress_callback(
                            DownloadProgress(
                                current_index=current_index,
                                total_files=total_files,
                                filename=destination.name,
                                bytes_downloaded=ByteCount(downloaded_bytes),
                                file_size_bytes=ByteCount(target_bytes or downloaded_bytes),
                                speed_mbps=MegabitsPerSecond(speed_mbps),
                                elapsed_seconds=elapsed,
                                is_skipped=False,
                                is_completed=False,
                                start_time=str(recording.start),
                                end_time=str(recording.end),
                            )
                        )
                        last_emit_time = now

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
                    is_completed=True,
                    start_time=str(recording.start),
                    end_time=str(recording.end),
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
    port: int = 80,
    timeout: float = 120.0,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> DownloadResult:
    """Download a slice of recordings sequentially and return aggregate statistics."""
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

    for batch_idx, offset in enumerate(range(start, start + count), start=1):
        recording = selected[batch_idx - 1]

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
            current_index=batch_idx,
            total_files=count,
            port=port,
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


def download_recordings_concurrent(
    session: requests.Session,
    host: str,
    recordings: Sequence[Recording],
    track_id: TrackId,
    output_dir: Path,
    start: int,
    count: int,
    max_workers: int = 2,
    port: int = 80,
    timeout: float = 120.0,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> DownloadResult:
    """Download a slice of recordings concurrently using a bounded thread pool."""
    total_recordings = len(recordings)
    if start < 1 or start > total_recordings:
        raise ValueError(f"Start index {start} out of bounds (1..{total_recordings})")
    if count < 1:
        raise ValueError(f"Count must be >= 1, got {count}")
    if start + count - 1 > total_recordings:
        raise ValueError(f"Range {start}..{start + count - 1} exceeds total recordings {total_recordings}")

    # Enforce strict safety clamp: 1 <= workers <= 4
    effective_workers = max(1, min(max_workers, 4))

    selected = recordings[start - 1 : start - 1 + count]
    batch_started = time.monotonic()

    downloaded_files = 0
    skipped_files = 0
    downloaded_bytes = 0
    failed_index: int | None = None
    error_message: str | None = None

    lock = threading.Lock()
    local_cancel_event = cancel_event or threading.Event()

    def _worker_task(offset: int, batch_idx: int, recording: Recording) -> tuple[int, bool, float, ByteCount, bool, str | None]:
        if local_cancel_event.is_set():
            return offset, False, 0.0, ByteCount(0), False, "Download cancelled"

        filename = f"{offset}_{recording.name}" if recording.name.endswith(".mp4") else f"{offset}_{recording.name}.mp4"
        destination = output_dir / filename

        success, duration, actual_size, is_skipped, error_msg = download_recording(
            session=session,
            host=host,
            recording=recording,
            track_id=track_id,
            destination=destination,
            current_index=batch_idx,
            total_files=count,
            port=port,
            timeout=timeout,
            progress_callback=progress_callback,
            cancel_event=local_cancel_event,
        )

        return offset, success, duration, actual_size, is_skipped, error_msg

    with ThreadPoolExecutor(max_workers=effective_workers) as executor:
        futures = [
            executor.submit(_worker_task, offset, batch_idx, recording)
            for batch_idx, (offset, recording) in enumerate(
                [(start + i, rec) for i, rec in enumerate(selected)],
                start=1,
            )
        ]


        for future in as_completed(futures):
            try:
                offset, success, _duration, actual_size, is_skipped, error_msg = future.result()
            except (requests.RequestException, OSError, RuntimeError, ValueError) as exc:
                success = False
                offset = start
                actual_size = ByteCount(0)
                is_skipped = False
                error_msg = str(exc)

            with lock:
                if not success:
                    if failed_index is None:
                        failed_index = offset
                        error_message = error_msg
                        local_cancel_event.set()
                else:
                    if is_skipped:
                        skipped_files += 1
                    else:
                        downloaded_files += 1
                        downloaded_bytes += int(actual_size)

    total_duration = time.monotonic() - batch_started

    if failed_index is not None:
        return DownloadResult(
            success=False,
            total_files=count,
            downloaded_files=downloaded_files,
            skipped_files=skipped_files,
            downloaded_bytes=ByteCount(downloaded_bytes),
            total_duration_seconds=total_duration,
            failed_index=failed_index,
            error_message=error_message,
        )

    return DownloadResult(
        success=True,
        total_files=count,
        downloaded_files=downloaded_files,
        skipped_files=skipped_files,
        downloaded_bytes=ByteCount(downloaded_bytes),
        total_duration_seconds=total_duration,
        failed_index=None,
        error_message=None,
    )
