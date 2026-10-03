# Implementation Plan - Task 007-zk: True Multi-Threaded Concurrent Downloads, Per-Worker Progress, Calendar Navigation & Table Padding

## 1. Analysis of Task Requirements
1. **Real Concurrent Downloads (`workers.py`):**
   - Replace sequential group download loop in `DownloadWorker` with `concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)`.
   - Manage worker IDs `1..max_workers` using a thread-safe `queue.Queue[int]`.
   - Emit `signal_file_started(filename: str, worker_id: int)` when each download begins.
   - Run parallel segment downloads with thread-safe aggregations (Lock) for file counts, byte counters, and completion signals.
2. **Live Row Status & Multi-Worker Console Feedback (`main_window.py`, `models.py`):**
   - In `models.py`, support `item.status.startswith("Downloading")` for cyan styling `#38BDF8`.
   - In `main_window.py`, connect `signal_file_started` to set row status to `"Downloading"`.
   - During progress callbacks, update row status to `"Downloading (XX%)"`.
   - In the Live Console progress area, format multi-worker progress:
     `Worker 1: [filename1] 45% (3.2 MB/s) | Worker 2: [filename2] 12% (2.9 MB/s)`.
3. **Dark/Light Mode Calendar Navigation Arrows (`style.py`):**
   - Explicitly style `QCalendarWidget QToolButton`, `#qt_calendar_prevmonth`, and `#qt_calendar_nextmonth` with high-contrast text and background colors (`#F8FAFC`, `#334155` for dark theme, `#1E293B`, `#E2E8F0` for light theme).
4. **Left Panel Header & Table Column Widths (`main_window.py`):**
   - Rename `"Deselect"` button above cameras to `"Clear"`.
   - Set fixed column widths on both Left (Cameras) and Right (Recordings) tables:
     - `COL_CHECK`: `28px` (fixed).
     - `COL_NUM`: `30px` (fixed, centered).

## 2. Target Files
- `src/hikvision_downloader/ui/workers.py`: Concurrent ThreadPoolExecutor refactor in `DownloadWorker`, `signal_file_started` signal.
- `src/hikvision_downloader/ui/models.py`: Row status highlighting for `"Downloading (XX%)"` and status updates.
- `src/hikvision_downloader/ui/main_window.py`: Multi-worker live tracking, "Clear" button rename, column width adjustments (`28px`, `30px`).
- `src/hikvision_downloader/ui/style.py`: Calendar widget stylesheet rules in `DARK_THEME_QSS` and `LIGHT_THEME_QSS`.
- `tests/unit/test_ui.py`: New unit tests for concurrent download worker, worker progress reporting, calendar styles, and table column widths.

## 3. Proposed Logic & Changes

### `src/hikvision_downloader/ui/workers.py`
- Add `signal_file_started = Signal(str, int)` to `DownloadWorker`.
- In `DownloadWorker.run()`:
  - Create directories and write CSV manifests for all groups upfront.
  - Flatten work into `work_items: list[tuple[int, int, RecordingItem, Path, str]]`.
  - Maintain a thread-safe `worker_queue: queue.Queue[int]` with IDs `1..self.max_workers`.
  - In `_download_task(global_idx, local_idx, item, dest_dir, target_filename)`:
    - Get `worker_id` from `worker_queue`.
    - Emit `self.signal_file_started.emit(item.filename, worker_id)`.
    - Log `[Worker {worker_id}] [{global_idx}/{total_files}] Downloading {target_filename}...`.
    - Call `download_recording(...)`.
    - In `finally`, return `worker_id` to `worker_queue`.
  - Submit tasks via `ThreadPoolExecutor(max_workers=self.max_workers)`.
  - Process completed tasks via `as_completed(futures)` protected with `threading.Lock()`.
  - Emit `signal_file_completed` and `signal_finished`.

### `src/hikvision_downloader/ui/models.py`
- In `RecordingsTableModel.data()` for `ForegroundRole`:
  - Check `if item.status == "Downloading" or item.status.startswith("Downloading"):` -> return `#38BDF8`.

### `src/hikvision_downloader/ui/main_window.py`
- In `_create_cameras_panel()`:
  - Rename `btn_deselect_all = QPushButton("Deselect", self)` -> `btn_deselect_all = QPushButton("Clear", self)`.
  - Update `cameras_table`: `COL_CHECK` = 28, `COL_NUM` = 30.
- In `_create_recordings_panel()`:
  - Update `table_view`: `COL_CHECK` = 28, `COL_NUM` = 30.
- In download lifecycle:
  - Add state dictionary `self._worker_status: dict[int, dict[str, Any]]` and `self._file_to_worker: dict[str, int]`.
  - Connect `self._download_worker.signal_file_started.connect(self._on_file_started)`.
  - In `_on_file_started(filename, worker_id)`:
    - Update worker status: `active=True, filename=filename, percent=0, speed_mbps=0.0`.
    - Update table row status: `Downloading`.
    - Update live progress readout.
  - In `_on_download_progress(prog)`:
    - Calculate `file_percent = int(prog.bytes_downloaded / max(prog.file_size_bytes, 1) * 100)`.
    - Update table row status: `f"Downloading ({file_percent}%)"`.
    - Update worker status dictionary with percent and speed (MB/s).
    - Update live progress readout with multi-worker activity string:
      `Worker 1: [filename1] 45% (3.2 MB/s) | Worker 2: [filename2] 12% (2.9 MB/s)`.
  - In `_on_file_completed(filename, status, is_skipped)`:
    - Update table row status: `status`.
    - Mark corresponding worker inactive.

### `src/hikvision_downloader/ui/style.py`
- In `DARK_THEME_QSS` and `LIGHT_THEME_QSS`:
  - Add styling rules for `QCalendarWidget QWidget#qt_calendar_navigationbar`, `QCalendarWidget QToolButton`, `#qt_calendar_prevmonth`, `#qt_calendar_nextmonth`, `QCalendarWidget QMenu`, `QCalendarWidget QSpinBox`, `QCalendarWidget QTableView`.
  - Explicitly set `color: #F8FAFC; background-color: #334155;` in Dark mode for clear navigation arrow contrast.

## 4. Verification & Testing Plan
1. **Unit Tests:**
   - Test concurrent execution in `DownloadWorker` with 2 workers downloading 2 items concurrently, asserting `signal_file_started` emission and worker IDs 1 and 2.
   - Test `RecordingsTableModel` status display and coloring for `"Downloading (45%)"`.
   - Test column widths (28px and 30px) for both Camera and Recordings tables.
   - Test calendar stylesheet classes in `DARK_THEME_QSS` and `LIGHT_THEME_QSS`.
2. **Quality Gates:**
   - Run `uv run pytest tests/unit/test_ui.py`.
   - Run full test suite: `uv run pytest`.
   - Run strict type checking: `uv run mypy src tests`.
   - Run linter: `uv run ruff check .`.
3. **Walkthrough Document:**
   - Create `.gemini/logs/task-007-zl-walkthrough.md` documenting implementation details and test outputs.
