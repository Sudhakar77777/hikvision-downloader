"""Background QThread workers for non-blocking NVR operations in the Qt desktop UI."""

import threading
import time
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

import requests
from pydantic import SecretStr
from PySide6.QtCore import QObject, QThread, Signal

from ..core.auth import create_authenticated_session
from ..core.cameras import CameraDiscoveryService
from ..core.dates import discover_available_dates
from ..core.downloads import download_recording
from ..core.models import (
    ByteCount,
    Camera,
    CameraNumber,
    DownloadProgress,
    DownloadResult,
    Recording,
    TrackId,
)
from ..core.recordings import (
    build_search_xml,
    parse_search_response,
    save_recording_list,
)
from ..http_client import request_with_retry
from .models import RecordingItem


class AuthWorker(QThread):
    """Background worker for testing credentials and creating an authenticated NVR session."""

    signal_started = Signal()
    signal_finished = Signal(bool, str, object)  # success, message, session
    signal_log = Signal(str, str)  # level, message

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str | SecretStr,
        auth_type: str = "digest",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.host = host.strip()
        self.port = port
        self.username = username.strip()
        self.password = password
        self.auth_type = auth_type

    def run(self) -> None:
        self.signal_started.emit()
        self.signal_log.emit("INFO", f"Authenticating with NVR at {self.host}:{self.port} as '{self.username}'...")

        try:
            session = create_authenticated_session(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                auth_type=self.auth_type,
            )

            # Test connection with a fast single-request probe
            host_str = self.host if (":" in self.host or self.port == 80) else f"{self.host}:{self.port}"
            test_url = f"http://{host_str}/ISAPI/System/deviceInfo"

            resp = request_with_retry(session, "GET", test_url, timeout=10.0, max_retries=1)

            if resp.status_code in (200, 204):
                self.signal_log.emit("SUCCESS", f"Successfully authenticated with NVR ({self.host}:{self.port}).")
                self.signal_finished.emit(True, "Connected successfully", session)
            elif resp.status_code in (401, 403):
                self.signal_log.emit("ERROR", f"Authentication failed (HTTP {resp.status_code}). Check username or password.")
                self.signal_finished.emit(False, f"Authentication failed (HTTP {resp.status_code})", None)
            else:
                self.signal_log.emit("WARN", f"NVR responded with HTTP {resp.status_code}, connection established.")
                self.signal_finished.emit(True, f"Connected (HTTP {resp.status_code})", session)

        except requests.HTTPError as http_err:
            status = http_err.response.status_code if http_err.response is not None else "Error"
            msg = f"NVR Authentication error: HTTP {status}"
            self.signal_log.emit("ERROR", msg)
            self.signal_finished.emit(False, msg, None)
        except (requests.RequestException, OSError, RuntimeError, ValueError, TimeoutError) as exc:
            msg = f"Connection failed: {exc}"
            self.signal_log.emit("ERROR", msg)
            self.signal_finished.emit(False, msg, None)


class DiscoveryWorker(QThread):
    """Background worker for dynamic ISAPI camera discovery."""

    signal_started = Signal()
    signal_cameras = Signal(object)  # dict[CameraNumber, Camera]
    signal_device_info = Signal(object)  # dict[str, str]
    signal_error = Signal(str)
    signal_log = Signal(str, str)

    def __init__(
        self,
        session: requests.Session,
        host: str,
        port: int = 80,
        force_refresh: bool = False,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.host = host
        self.port = port
        self.force_refresh = force_refresh
        self._service = CameraDiscoveryService()

    def run(self) -> None:
        self.signal_started.emit()
        self.signal_log.emit("INFO", f"Discovering cameras on NVR {self.host}:{self.port} (force_refresh={self.force_refresh})...")

        # Attempt to retrieve device hardware metadata
        device_info: dict[str, str] = {}
        try:
            host_str = self.host if (":" in self.host or self.port == 80) else f"{self.host}:{self.port}"
            resp = request_with_retry(self.session, "GET", f"http://{host_str}/ISAPI/System/deviceInfo", timeout=10.0)
            root = ET.fromstring(resp.text)
            for child in root.iter():
                tag = child.tag.split("}")[-1]
                if child.text:
                    device_info[tag] = child.text.strip()
        except (requests.RequestException, ET.ParseError, OSError, ValueError) as exc:
            self.signal_log.emit("DEBUG", f"Device info query skipped: {exc}")

        if device_info:
            self.signal_device_info.emit(device_info)

        try:
            cameras = self._service.get_cameras(
                session=self.session,
                host=self.host,
                port=self.port,
                force_refresh=self.force_refresh,
            )
            count = len(cameras)
            self.signal_log.emit("SUCCESS", f"Discovered {count} camera channels on NVR.")
            self.signal_cameras.emit(cameras)
        except (requests.RequestException, OSError, RuntimeError, ValueError) as exc:
            msg = f"Camera discovery error: {exc}"
            self.signal_log.emit("ERROR", msg)
            self.signal_error.emit(msg)


_DEFAULT_DISCOVERY_TRACK: TrackId = TrackId(101)


class DatesWorker(QThread):
    """Background worker for discovering dates containing CCTV recordings."""

    signal_started = Signal()
    signal_dates = Signal(object)  # dict[tuple[int, int], list[RecordingDate]]
    signal_error = Signal(str)
    signal_log = Signal(str, str)

    def __init__(
        self,
        session: requests.Session,
        host: str,
        discovery_track_id: TrackId = _DEFAULT_DISCOVERY_TRACK,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.host = host
        self.discovery_track_id = discovery_track_id

    def run(self) -> None:
        self.signal_started.emit()
        self.signal_log.emit("INFO", f"Checking recording date distribution on NVR {self.host}...")

        try:
            dates_by_month, _duration = discover_available_dates(
                session=self.session,
                host=self.host,
                discovery_track_id=self.discovery_track_id,
            )
            total_days = sum(len(days) for days in dates_by_month.values())
            self.signal_log.emit("SUCCESS", f"Discovered {total_days} days with recorded footage on NVR.")
            self.signal_dates.emit(dates_by_month)
        except (requests.RequestException, OSError, RuntimeError, ValueError) as exc:
            msg = f"Date distribution query error: {exc}"
            self.signal_log.emit("WARN", msg)
            self.signal_error.emit(msg)


class SearchWorker(QThread):
    """Background worker for querying CMSearch across multiple selected cameras."""

    signal_started = Signal()
    signal_progress = Signal(int, int, str)  # current_cam, total_cams, cam_name
    signal_camera_recordings = Signal(object, str, object, object)  # Camera, stream_name, TrackId, list[Recording]
    signal_finished = Signal(int)  # total_recordings_count
    signal_error = Signal(str)
    signal_log = Signal(str, str)

    def __init__(
        self,
        session: requests.Session,
        host: str,
        port: int,
        camera_queries: list[tuple[Camera, str, TrackId]],
        target_date: date,
        start_time_str: str | None = None,
        end_time_str: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.host = host
        self.port = port
        self.camera_queries = camera_queries
        self.target_date = target_date
        self.start_time_str = start_time_str or f"{target_date.isoformat()}T00:00:00Z"
        self.end_time_str = end_time_str or f"{target_date.isoformat()}T23:59:59Z"
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Cancel ongoing search queries."""
        self._cancel_event.set()

    def run(self) -> None:
        self.signal_started.emit()
        total_queries = len(self.camera_queries)
        self.signal_log.emit(
            "INFO",
            f"Searching recordings for date {self.target_date.isoformat()} ({self.start_time_str} to {self.end_time_str}) across {total_queries} camera channels...",
        )

        total_found = 0
        host_str = self.host if (":" in self.host or self.port == 80) else f"{self.host}:{self.port}"
        url = f"http://{host_str}/ISAPI/ContentMgmt/search"

        try:
            for idx, (camera, stream_name, track_id) in enumerate(self.camera_queries, start=1):
                if self._cancel_event.is_set():
                    self.signal_log.emit("WARN", "Search operation aborted by operator.")
                    break

                self.signal_progress.emit(idx, total_queries, camera.display_name)
                self.signal_log.emit(
                    "INFO",
                    f"[{idx}/{total_queries}] Querying {camera.display_name} ({stream_name}, track {track_id})...",
                )

                cam_recordings: list[Recording] = []
                position = 0
                batch_size = 50

                while not self._cancel_event.is_set():
                    xml_payload = build_search_xml(
                        track_id=track_id,
                        start_time=self.start_time_str,
                        end_time=self.end_time_str,
                        position=position,
                        batch_size=batch_size,
                    )

                    try:
                        resp = request_with_retry(
                            self.session,
                            "POST",
                            url,
                            data=xml_payload.encode("utf-8"),
                            headers={"Content-Type": "application/xml"},
                            timeout=60.0,
                        )
                        batch = parse_search_response(resp.text)
                    except requests.HTTPError as http_err:
                        if http_err.response is not None and http_err.response.status_code == 400:
                            # 400 Bad Request if track has no recordings configured
                            batch = []
                        else:
                            raise

                    if not batch:
                        break

                    cam_recordings.extend(batch)
                    if len(batch) < batch_size:
                        break

                    position += batch_size

                count_for_cam = len(cam_recordings)
                total_found += count_for_cam
                self.signal_log.emit(
                    "SUCCESS" if count_for_cam > 0 else "INFO",
                    f"Found {count_for_cam} recording segments for {camera.display_name} ({stream_name}).",
                )
                self.signal_camera_recordings.emit(camera, stream_name, track_id, cam_recordings)

            self.signal_finished.emit(total_found)
            self.signal_log.emit("SUCCESS", f"Search completed: total {total_found} recording segments discovered.")

        except (requests.RequestException, OSError, RuntimeError, ValueError) as exc:
            msg = f"Search query error: {exc}"
            self.signal_log.emit("ERROR", msg)
            self.signal_error.emit(msg)


class DownloadWorker(QThread):
    """Background worker orchestrating concurrent batch downloads across selected segments."""

    signal_started = Signal()
    signal_progress = Signal(object)  # DownloadProgress
    signal_file_completed = Signal(str, str, bool)  # filename, status, is_skipped
    signal_finished = Signal(object)  # DownloadResult
    signal_error = Signal(str)
    signal_log = Signal(str, str)

    def __init__(
        self,
        session: requests.Session,
        host: str,
        port: int,
        selected_items: list[RecordingItem],
        output_root: Path,
        max_workers: int = 2,
        save_csv: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.host = host
        self.port = port
        self.selected_items = list(selected_items)
        self.output_root = Path(output_root)
        self.max_workers = max(1, min(max_workers, 4))
        self.save_csv = save_csv
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Signal cancellation to all in-flight downloads."""
        self._cancel_event.set()

    def run(self) -> None:
        self.signal_started.emit()
        total_files = len(self.selected_items)

        if total_files == 0:
            self.signal_finished.emit(
                DownloadResult(
                    success=True,
                    total_files=0,
                    downloaded_files=0,
                    skipped_files=0,
                    downloaded_bytes=ByteCount(0),
                    total_duration_seconds=0.0,
                )
            )
            return

        total_bytes = sum(item.size_bytes for item in self.selected_items)
        self.signal_log.emit(
            "INFO",
            f"Initiating batch download: {total_files} segments ({total_bytes / (1024 * 1024):.1f} MB) using {self.max_workers} concurrent workers...",
        )

        # Group items by camera, stream, and date for proper subfolder organisation
        groups: dict[tuple[int, str, str, str], list[tuple[int, RecordingItem]]] = {}
        for global_idx, item in enumerate(self.selected_items, start=1):
            date_str = item.recording.start.split("T")[0].replace("-", "")
            cam_num = int(item.camera.number)
            cam_name = item.camera.name
            stream = item.stream.upper()
            key = (cam_num, cam_name, stream, date_str)
            if key not in groups:
                groups[key] = []
            groups[key].append((global_idx, item))

        batch_start_time = time.monotonic()
        downloaded_count = 0
        skipped_count = 0
        downloaded_bytes = 0
        failed_idx: int | None = None
        error_msg: str | None = None

        lock = threading.Lock()

        # Thread-safe progress adapter
        def _progress_adapter(prog: DownloadProgress) -> None:
            self.signal_progress.emit(prog)

        for (cam_num, cam_name, stream, date_str), group_items in groups.items():
            if self._cancel_event.is_set():
                break

            folder_name = f"{date_str}_D{cam_num}_{cam_name.replace(' ', '_')}_{stream}"
            dest_dir = self.output_root / folder_name
            dest_dir.mkdir(parents=True, exist_ok=True)

            if self.save_csv and group_items:
                try:
                    recs_in_group = [item.recording for _, item in group_items]
                    first_date = date.fromisoformat(group_items[0][1].recording.start.split("T")[0])
                    save_recording_list(
                        recordings=recs_in_group,
                        output_dir=dest_dir,
                        camera_number=CameraNumber(cam_num),
                        camera_name=cam_name.replace(" ", "_"),
                        stream_name=stream,
                        recording_date=first_date,
                    )
                except (OSError, ValueError) as csv_err:
                    self.signal_log.emit("WARN", f"Could not write CSV manifest: {csv_err}")

            # Download items in this group
            for local_idx, (global_idx, item) in enumerate(group_items, start=1):
                if self._cancel_event.is_set():
                    break

                target_filename = f"{local_idx}_{item.filename}" if item.filename.endswith(".mp4") else f"{local_idx}_{item.filename}.mp4"
                destination = dest_dir / target_filename

                self.signal_log.emit("INFO", f"[{global_idx}/{total_files}] Downloading {target_filename}...")

                success, duration, actual_size, is_skipped, err = download_recording(
                    session=self.session,
                    host=self.host,
                    recording=item.recording,
                    track_id=item.track_id,
                    destination=destination,
                    current_index=global_idx,
                    total_files=total_files,
                    port=self.port,
                    timeout=120.0,
                    progress_callback=_progress_adapter,
                    cancel_event=self._cancel_event,
                )

                with lock:
                    if not success:
                        if failed_idx is None:
                            failed_idx = global_idx
                            error_msg = err or "Download failed"
                            self._cancel_event.set()
                        self.signal_file_completed.emit(item.filename, "Failed", False)
                        self.signal_log.emit("ERROR", f"Failed {target_filename}: {err}")
                    else:
                        if is_skipped:
                            skipped_count += 1
                            self.signal_file_completed.emit(item.filename, "Skipped", True)
                            self.signal_log.emit("SKIP", f"Skipped (already exists): {target_filename}")
                        else:
                            downloaded_count += 1
                            downloaded_bytes += int(actual_size)
                            self.signal_file_completed.emit(item.filename, "Completed", False)
                            speed_mbps = (int(actual_size) * 8.0 / duration / 1_000_000.0) if duration > 0 else 0.0
                            self.signal_log.emit(
                                "SUCCESS",
                                f"Saved {target_filename} ({int(actual_size) / (1024 * 1024):.1f} MB in {duration:.1f}s, {speed_mbps:.1f} Mbps)",
                            )

        total_duration = time.monotonic() - batch_start_time

        if self._cancel_event.is_set() and failed_idx is None:
            self.signal_log.emit("WARN", "Batch download cancelled by user.")
            result = DownloadResult(
                success=False,
                total_files=total_files,
                downloaded_files=downloaded_count,
                skipped_files=skipped_count,
                downloaded_bytes=ByteCount(downloaded_bytes),
                total_duration_seconds=total_duration,
                failed_index=failed_idx,
                error_message="Batch download cancelled by operator",
            )
        elif failed_idx is not None:
            result = DownloadResult(
                success=False,
                total_files=total_files,
                downloaded_files=downloaded_count,
                skipped_files=skipped_count,
                downloaded_bytes=ByteCount(downloaded_bytes),
                total_duration_seconds=total_duration,
                failed_index=failed_idx,
                error_message=error_msg,
            )
        else:
            self.signal_log.emit(
                "SUCCESS",
                f"Batch download complete! {downloaded_count} downloaded, {skipped_count} skipped ({downloaded_bytes / (1024 * 1024):.1f} MB total in {total_duration:.1f}s).",
            )
            result = DownloadResult(
                success=True,
                total_files=total_files,
                downloaded_files=downloaded_count,
                skipped_files=skipped_count,
                downloaded_bytes=ByteCount(downloaded_bytes),
                total_duration_seconds=total_duration,
            )

        self.signal_finished.emit(result)
