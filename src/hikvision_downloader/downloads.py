import time

from .config import NVR_HOST, TIMEOUT
from .http_client import request_with_retry

# ============================================================
# Timing
# ============================================================


def format_duration(seconds):
    """Format seconds as HH:MM:SS or seconds."""

    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes, secs = divmod(int(seconds), 60)

    if minutes < 60:
        return f"{minutes}m {secs:02d}s"

    hours, minutes = divmod(minutes, 60)

    return f"{hours}h {minutes:02d}m {secs:02d}s"


# ============================================================
# Download
# ============================================================


def build_download_url(recording, track_id):
    """Build the download URL in the same form used by the Hikvision web UI."""

    playback_uri = (
        f"rtsp://{NVR_HOST}"
        f"/Streaming/tracks/{track_id}"
        f"?starttime={recording.start.replace('T', ' ')}"
        f"&amp;endtime={recording.end.replace('T', ' ')}"
        f"&amp;name={recording.name}"
        f"&amp;size={recording.size}"
    )

    return f"http://{NVR_HOST}/ISAPI/ContentMgmt/download?playbackURI={playback_uri}&onlyVerification=true"


def download_recording(session, recording, track_id, destination, number, total):
    """Download exactly one recording and return success, duration, and bytes."""

    if not recording.name:
        print(f"[{number}/{total}] ERROR: recording has no name")
        return False, 0.0, 0

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        actual_size = destination.stat().st_size

        if actual_size > 0:
            size_mb = actual_size / (1024 * 1024)
            print(f"[{number}/{total}] {destination.name}  {size_mb:.2f} MB  SKIP")
            return True, 0.0, actual_size

    url = build_download_url(recording, track_id)
    temp_file = destination.with_suffix(destination.suffix + ".part")

    started = time.monotonic()

    try:
        response = request_with_retry(
            session,
            "GET",
            url,
            stream=True,
            timeout=TIMEOUT,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "*/*",
                "If-Modified-Since": "0",
            },
        )

        with response, open(temp_file, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)

        actual_size = temp_file.stat().st_size
        duration = time.monotonic() - started

        if actual_size == 0:
            print(f"[{number}/{total}] {destination.name}  ERROR: empty file")
            temp_file.unlink(missing_ok=True)
            return False, duration, 0

        temp_file.rename(destination)

        size_mb = actual_size / (1024 * 1024)

        print(f"[{number}/{total}] {destination.name}  {size_mb:.2f} MB  {format_duration(duration)}  OK")

        return True, duration, actual_size

    except (OSError, ValueError, RuntimeError) as exc:
        duration = time.monotonic() - started

        print(f"[{number}/{total}] {destination.name}  ERROR: {exc}")

        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass

        return False, duration, 0


def download_recordings(session, recordings, track_id, output_dir, start, count):
    """Download the selected recording range and return aggregate statistics."""

    selected = recordings[start - 1 : start - 1 + count]

    batch_started = time.monotonic()
    downloaded_files = 0
    skipped_files = 0
    downloaded_bytes = 0
    total_download_time = 0.0

    for offset, recording in enumerate(selected, start=start):
        destination = output_dir / f"{offset}_{recording.name}.mp4"

        success, duration, actual_size = download_recording(
            session,
            recording,
            track_id,
            destination,
            offset,
            len(recordings),
        )

        if not success:
            return {
                "success": False,
                "batch_duration": time.monotonic() - batch_started,
                "downloaded_files": downloaded_files,
                "skipped_files": skipped_files,
                "downloaded_bytes": downloaded_bytes,
                "total_download_time": total_download_time,
                "failed_number": offset,
            }

        total_download_time += duration

        if duration == 0:
            skipped_files += 1
        else:
            downloaded_files += 1
            downloaded_bytes += actual_size

    return {
        "success": True,
        "batch_duration": time.monotonic() - batch_started,
        "downloaded_files": downloaded_files,
        "skipped_files": skipped_files,
        "downloaded_bytes": downloaded_bytes,
        "total_download_time": total_download_time,
        "failed_number": None,
    }
