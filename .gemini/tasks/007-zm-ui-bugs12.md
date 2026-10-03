CRITICAL BUG FIX: PARALLEL DOWNLOAD STALLING ON SHARED SESSION & TELEMETRY PROGRESS MISATTRIBUTION

Workers 2, 3, and 4 stall at 0% (0.0 MB/s) because `DownloadWorker` shares a single `requests.Session` across threads, causing `requests.auth.HTTPDigestAuth` nonce collisions and `urllib3` connection serialization[cite: 36, 41]. In addition, progress callbacks rely on filename string heuristics in `MainWindow`, misattributing events to Worker 1[cite: 36, 38].

Refactor `src/hikvision_downloader/ui/` to guarantee true parallel downloads, per-worker authenticated sessions, and direct worker ID telemetry binding. Follow `.gemini/rules/4-coding-standards.md` strictly (100% explicit type annotations).

---

### 1. Dedicated Per-Worker Sessions & Connection Isolation (`workers.py`)
- In `DownloadWorker`:
  - Do NOT share a single `requests.Session` across concurrent threads for streaming downloads[cite: 41].
  - Update `__init__` to accept authentication parameters needed to instantiate independent worker sessions:
    ```python
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str | SecretStr,
        auth_type: str = "digest",
        selected_items: list[RecordingItem] = ...,
        output_root: Path = ...,
        max_workers: int = 2,
        save_csv: bool = True,
        parent: QObject | None = None,
    ) -> None:
    ```
  - In `run()`:
    - Pre-allocate a dedicated `requests.Session` for each worker ID (1 to `self.max_workers`) using `create_authenticated_session(host, port, username, password, auth_type)`[cite: 41].
    - Store them in a lookup mapping: `worker_sessions: dict[int, requests.Session]`.
    - When a thread checks out `worker_id = worker_id_queue.get()`, pass `session = worker_sessions[worker_id]` to `download_recording(session=session, ...)`.
    - Upon thread pool termination, cleanly close all sessions in `worker_sessions.values()`.

---

### 2. Direct Worker ID Binding in Progress Callbacks (`workers.py`)
- Change the progress signal definition to bind the worker ID explicitly:
  ```python
  signal_progress = Signal(int, object)  # worker_id: int, progress: DownloadProgress

```

* Inside `_download_task()`:
* Eliminate all filename-guessing heuristics.


* Bind `worker_id` directly in the progress callback closure:
```python
last_emit_time = 0.0

def _progress_adapter(prog: DownloadProgress) -> None:
    nonlocal last_emit_time
    now = time.monotonic()
    # Throttle emissions to at most once every 100ms per worker, or on complete/skipped
    if prog.is_completed or prog.is_skipped or (now - last_emit_time >= 0.1):
        last_emit_time = now
        self.signal_progress.emit(worker_id, prog)

```

---

### 3. Direct Route Telemetry in `MainWindow` (`main_window.py`)

* In `_on_start_download_clicked()`:
* Instantiate `DownloadWorker` passing `username` and `password` (extracted from the active credentials) rather than passing the single shared `self._session`.


* Update the progress handler signature and routing:
```python
def _on_download_progress(self, worker_id: int, prog: DownloadProgress) -> None:

```

* Remove all fallback blocks where `worker_id` defaults to 1:
* Use `worker_id` directly to update `self._worker_widgets[worker_id]`.
* Update `self._worker_widgets[worker_id].progress_bar.setValue(file_percent)`.
* Update `self._worker_widgets[worker_id].detail_label.setText(...)` with that worker's specific file name, percentage, and MB/s throughput.
* Update the matching table row's status column: `Downloading ({file_percent}%)`.
---

### 4. Verification Suite & Unit Tests (`tests/unit/test_ui.py`)
* Update `test_download_worker_concurrent_two_workers` and existing UI test cases to verify:
1. `signal_progress` emits `(worker_id, DownloadProgress)` with accurate `worker_id` matching the executing slot.
2. Each active worker maintains an isolated session without blocking other active workers.

* Run the full verification suite:
```bash
uv run pytest tests/unit/test_ui.py
uv run pytest
uv run mypy src tests
uv run ruff check .

```


* Document the root cause, session architecture changes, and verification test logs in `.gemini/logs/task-007-zm-walkthrough.md`.

