# Implementation Plan - Task 007-zm: Dedicated Per-Worker Sessions & Direct Worker ID Telemetry

## 1. Analysis of Task Requirements
1. **Parallel Download Stalling on Shared Session (`workers.py`):**
   - **Root Cause:** When `DownloadWorker` spawns multiple concurrent worker threads using a single shared `requests.Session`, `urllib3` connection pooling serializes requests and `HTTPDigestAuth` nonces collide across threads, stalling Workers 2, 3, and 4 at 0% (0.0 MB/s).
   - **Remedy:** In `DownloadWorker`:
     - Update `__init__` to accept `host`, `port`, `username`, `password: str | SecretStr`, `auth_type: str = "digest"` (instead of accepting a shared `requests.Session`).
     - In `run()`: Pre-allocate an isolated `requests.Session` per worker (`worker_sessions: dict[int, requests.Session]`) via `create_authenticated_session(...)`.
     - When a worker checks out `worker_id`, pass `worker_sessions[worker_id]` to `download_recording(...)`.
     - After all worker threads complete or upon cancellation, explicitly close each session in `worker_sessions.values()`.

2. **Direct Worker ID Binding in Telemetry & Progress Callbacks (`workers.py`):**
   - **Root Cause:** `signal_progress` currently emits `(DownloadProgress,)`. `MainWindow` tries to deduce which worker produced the event using filename heuristics, leading to misattribution to Worker 1.
   - **Remedy:**
     - Update `DownloadWorker.signal_progress = Signal(int, object)` (emitting `worker_id: int`, `prog: DownloadProgress`).
     - In `_download_task`, create a throttled closure adapter `_progress_adapter(prog: DownloadProgress)` capturing `worker_id` and emitting `self.signal_progress.emit(worker_id, prog)` at most once every 100ms per worker (or immediately when complete/skipped).

3. **Direct Route Telemetry in `MainWindow` (`main_window.py`):**
   - In `_on_start_download_clicked()`:
     - Instantiate `DownloadWorker` with `host`, `port`, `username`, `password`, and `auth_type=NVR_AUTH_TYPE`.
   - Update `_on_download_progress(self, worker_id: int, prog: DownloadProgress) -> None`:
     - Remove all fallback heuristics and defaulting to Worker 1.
     - Directly route telemetry to `self._worker_widgets[worker_id]` and `self._worker_activities[worker_id]`.
     - Update the row status in the table model: `Downloading ({file_percent}%)`.
     - Call `_update_multi_worker_progress()`.

4. **Verification & Test Suite Updates (`tests/unit/test_ui.py`):**
   - Update all `DownloadWorker` unit tests to instantiate with credentials (`username`, `password`, `auth_type`) and verify `signal_progress` emission of `(worker_id, prog)`.
   - Add verification that each worker receives an isolated session instance without blocking.
   - Update direct calls to `_on_download_progress` to pass `worker_id`.
   - Execute full test suite, linting, and type checking (`pytest`, `mypy`, `ruff`).

## 2. Target Files
- `src/hikvision_downloader/ui/workers.py`: Per-worker session allocation and direct worker ID in `signal_progress`.
- `src/hikvision_downloader/ui/main_window.py`: Updated `DownloadWorker` instantiation and direct `worker_id` telemetry routing in `_on_download_progress`.
- `tests/unit/test_ui.py`: Updated unit tests for `DownloadWorker`, `MainWindow` progress routing, and per-worker isolated sessions.
- `.gemini/logs/task-007-zm-walkthrough.md`: Comprehensive walkthrough and verification log.

## 3. Proposed Logic & Changes

### `src/hikvision_downloader/ui/workers.py`
```python
class DownloadWorker(QThread):
    signal_started = Signal()
    signal_file_started = Signal(str, int)  # filename, worker_id
    signal_progress = Signal(int, object)  # worker_id, DownloadProgress
    signal_file_completed = Signal(str, str, bool)  # filename, status, is_skipped
    signal_finished = Signal(object)  # DownloadResult
    signal_error = Signal(str)
    signal_log = Signal(str, str)

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str | SecretStr,
        auth_type: str = "digest",
        selected_items: list[RecordingItem] | None = None,
        output_root: Path | None = None,
        max_workers: int = 2,
        save_csv: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.host = host.strip()
        self.port = port
        self.username = username.strip()
        self.password = password
        self.auth_type = auth_type
        self.selected_items = list(selected_items) if selected_items else []
        self.output_root = Path(output_root) if output_root else Path.cwd()
        self.max_workers = max(1, min(max_workers, 4))
        self.save_csv = save_csv
        self._cancel_event = threading.Event()
```
- In `run()`:
  - Create `worker_sessions: dict[int, requests.Session] = {}` allocating dedicated session per `wid` in `range(1, self.max_workers + 1)`.
  - In `_download_task`:
    - `worker_id = worker_id_queue.get()`
    - `session = worker_sessions[worker_id]`
    - Pass `session=session` and `progress_callback=_progress_adapter` to `download_recording(...)`.
    - `_progress_adapter` throttles emissions (100ms interval or completion) and emits `self.signal_progress.emit(worker_id, prog)`.
  - In `finally` block after `ThreadPoolExecutor`:
    - Cleanly close each session in `worker_sessions.values()`.

### `src/hikvision_downloader/ui/main_window.py`
- In `_on_start_download_clicked()`:
  ```python
  host = self.host_input.text()
  port = self.port_input.value()
  username = self.user_input.text()
  password = self.password_input.text()
  workers = self.worker_slider.value()
  save_csv = self.csv_manifest_cb.isChecked()

  self._download_worker = DownloadWorker(
      host=host,
      port=port,
      username=username,
      password=password,
      auth_type=NVR_AUTH_TYPE,
      selected_items=selected_items,
      output_root=out_path,
      max_workers=workers,
      save_csv=save_csv,
      parent=self,
  )
  ```
- In `_on_download_progress(self, worker_id: int, prog: DownloadProgress) -> None`:
  - Calculate `file_percent` and `speed_mb_s`.
  - Update row status in `_table_model`: `"Downloading ({file_percent}%)"`.
  - Update `self._worker_activities[worker_id]` directly without filename searches or fallback defaults.
  - Update `self._worker_widgets[worker_id].progress_bar` and `detail_label` directly.
  - Call `_update_multi_worker_progress()`.

### `tests/unit/test_ui.py`
- Update all tests constructing `DownloadWorker` or calling `_on_download_progress`.
- Add test verifying multiple concurrent workers use separate session instances and emit accurate `worker_id` telemetry.

## 4. Verification & Testing Plan
1. **Unit Tests:**
   - Run `uv run pytest tests/unit/test_ui.py` to confirm all GUI, worker, progress telemetry, and session isolation tests pass.
2. **Full Test Suite & Static Analysis:**
   - Run `uv run pytest` across all unit, functional, and integration tests.
   - Run `uv run mypy src tests` for strict type checking.
   - Run `uv run ruff check .` for linting standards.
3. **Walkthrough Document:**
   - Produce `.gemini/logs/task-007-zm-walkthrough.md` with detailed explanations and command outputs.
