# Walkthrough: Task 007-zk (True Multi-Threaded Concurrent Downloads, Per-Worker Progress, Calendar Navigation & Table Padding)

## Overview
We refactored `src/hikvision_downloader/ui/` to enable true multi-threaded concurrent segment downloads via `concurrent.futures.ThreadPoolExecutor`, live per-worker progress tracking in the terminal console, dynamic row status percentage feedback in the recordings table, enhanced Dark Mode navigation styling for calendar tool buttons, and tightened table column spacing.

## Changes Implemented

### 1. True Concurrent Downloads in Background Worker
- **File**: [workers.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/workers.py)
  - Replaced the single-threaded sequential group download loop with `ThreadPoolExecutor(max_workers=self.max_workers)`.
  - Added `signal_file_started = Signal(str, int)` emitting destination filename and assigned 1-based `worker_id`.
  - Managed bounded worker IDs via a thread-safe `queue.Queue[int]`.
  - Guaranteed thread-safe metric aggregation (byte counters, completion counters, error propagation) using `threading.Lock`.

### 2. Live Row Status & Multi-Worker Progress Feedback
- **File**: [models.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/models.py)
  - Enhanced `RecordingsTableModel.data()` for `ForegroundRole` so that any dynamic status starting with `"Downloading"` (e.g., `"Downloading (45%)"`) is styled in cyan (`#38BDF8`).
  - Improved `update_item_status()` to support full and prefixed filename lookups.
- **File**: [main_window.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py)
  - Added `WorkerActivity` dataclass and tracking dictionary `_worker_activities`.
  - Connected `signal_file_started` to `_on_file_started`, setting row status immediately to `"Downloading"`.
  - Updated `_on_download_progress` to update row status to `Downloading ({file_percent}%)` and render per-worker live activity in the console progress line:
    `Worker 1: [filename1] 45% (3.2 MB/s) | Worker 2: [filename2] 12% (2.9 MB/s)`.
  - Handled batch completion and thread-safe cancellation cleanly.

### 3. Dark & Light Theme Calendar Widget Navigation Arrows
- **File**: [style.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/style.py)
  - Explicitly styled `QCalendarWidget QToolButton`, `#qt_calendar_prevmonth`, and `#qt_calendar_nextmonth` in `DARK_THEME_QSS` with `color: #F8FAFC; background-color: #334155;` ensuring high contrast navigation arrows `<` and `>`.
  - Explicitly styled `QCalendarWidget QToolButton`, `#qt_calendar_prevmonth`, and `#qt_calendar_nextmonth` in `LIGHT_THEME_QSS`.

### 4. Left Panel Header & Column Padding
- **File**: [main_window.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py)
  - Renamed the `"Deselect"` button above the camera list to `"Clear"`.
  - Set fixed column widths for both Cameras and Recordings tables:
    - `COL_CHECK`: Width `28px` (fixed).
    - `COL_NUM`: Width `30px` (fixed, centered).

## Verification & Testing

### 1. Test Suite Results
Executed unit, functional, and integration tests across the codebase:
- `uv run pytest tests/unit/test_ui.py`: **33 passed** in 0.86s
- `uv run pytest`: **167 passed, 1 skipped** in 72.53s
- `uv run mypy src tests`: **Success (0 issues)**
- `uv run ruff check .`: **All checks passed (0 issues)**

### 2. New Test Coverage Added
- `test_download_worker_concurrent_two_workers`: Confirmed concurrent execution of 2 simultaneous downloads and emission of `signal_file_started`.
- `test_recordings_table_model_live_status_styling`: Confirmed `"Downloading (45%)"` row status renders with cyan foreground brush `#38BDF8`.
- `test_table_column_widths_and_clear_button`: Confirmed 28px/30px fixed widths on both tables and "Clear" button naming.
- `test_calendar_dark_light_theme_styles`: Confirmed Dark and Light theme stylesheet rules for calendar tool buttons.
- `test_main_window_multi_worker_progress_reporting`: Confirmed live `Worker 1: [filename1] 45% (3.2 MB/s) | Worker 2: [filename2] 12% (2.9 MB/s)` console formatting.
