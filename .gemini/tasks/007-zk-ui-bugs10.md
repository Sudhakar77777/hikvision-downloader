CRITICAL FIX: TRUE MULTI-THREADED CONCURRENT DOWNLOADS, PER-WORKER PROGRESS, CALENDAR ARROWS & TABLE PADDING

Refactor `src/hikvision_downloader/ui/` adhering strictly to `.gemini/rules/4-coding-standards.md` (100% type annotations).

### 1. Fix Sequential Download Loop with Real Concurrent Workers (`workers.py`)
- In `DownloadWorker`:
  - Replace the single-threaded sequential `for` loop with `concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)`.
  - When starting download of each file, emit `signal_file_started(filename, worker_id)`.
  - Download multiple segments in parallel according to `max_workers` (e.g. 2 workers active simultaneously).
  - Ensure thread-safe updating of global byte counters, progress callbacks, and completion signals.

### 2. Live Row Status & Multi-Worker Progress Feedback
- In `main_window.py` and `models.py`:
  - Connect `signal_file_started` to immediately mark the row's `Status` as `"Downloading"` upon connection start.
  - Update row `Status` with live percentage: `"Downloading (45%)"`.
  - In the Live Console progress area, show live activity for each active concurrent worker:
    `Worker 1: [filename1] 45% (3.2 MB/s) | Worker 2: [filename2] 12% (2.9 MB/s)`

### 3. Fix Dark Mode Calendar Widget Navigation Arrows
- In `style.py` under `DARK_THEME_QSS`:
  - Explicitly style `QCalendarWidget QToolButton`, `#qt_calendar_prevmonth`, and `#qt_calendar_nextmonth`:
    - `color: #F8FAFC;`
    - `background-color: #334155;`
    - Set clear contrast for arrows `<` and `>` in both Dark and Light themes.

### 4. Left Panel Header & Column Padding
- In `main_window.py`:
  - Rename `"Deselect"` button above cameras to `"Clear"`.
  - Tighten table columns on BOTH Left and Right tables:
    - `COL_CHECK`: Width `28px` (fixed).
    - `COL_NUM`: Width `30px` (fixed, centered).

### 5. Verification
- Verify that setting Concurrent Workers to 2 actively downloads 2 files simultaneously.
- Verify calendar navigation `<` and `>` arrows are clearly visible in Dark Mode.
- Run `uv run pytest tests/unit/test_ui.py`.
- Run `uv run mypy src tests` (100% strict type safety).
- Run `uv run ruff check .`.
- Present the updated walkthrough in `.gemini/logs/task-007-zl-walkthrough.md`.