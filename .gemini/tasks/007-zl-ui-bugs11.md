CRITICAL BUG FIX: CANCELLATION STATE PURGE (NO FALSE ERRORS) & VISUAL MULTI-WORKER PROGRESS BARS

Refactor `src/hikvision_downloader/ui/` adhering strictly to `.gemini/rules/2-security.md` and `.gemini/rules/4-coding-standards.md` (100% explicit type annotations).

### 1. Fix Cancellation Handling in `DownloadWorker` (`workers.py`)
- User cancellation is NOT a failure:
  - When `self._cancel_event.is_set()` fires during execution:
    - NEVER emit `Failed` or log `[ERROR] Failed ...: Download cancelled` for unstarted files.
    - Only files that were actively in-flight should emit `signal_file_completed(filename, "Aborted", False)`.
    - Remaining queued/unstarted files MUST remain in `"Pending"` status.
    - Stop thread pool execution cleanly without iterating or marking the rest of the queue.
  - Console Logging on Cancel:
    - Log a single clean warning line:
      `[WARN] Batch download aborted by operator. (X downloaded, Y skipped, Z aborted).`
    - Do NOT flood the console with red error lines.

### 2. Table Status Values for Cancellation (`models.py`)
- In `RecordingsTableModel`:
  - When status is `"Aborted"` or `"Cancelled"`:
    - Render foreground text in muted Amber/Yellow (`#F59E0B` dark / `#D97706` light).
    - Never paint user-aborted files as red `"Failed"`.

### 3. Dedicated Visual Multi-Worker Progress Bars (`main_window.py`)
- In `_build_console_log_panel()` (Tier 2 Progress Area):
  - Replace the single text label with a structured **Worker Progress Panel**:
    - **Top Row**: Overall Batch Progress Bar (`QProgressBar`, height `8px`) with batch summary text `[ X% ] 12/97 Files · 1.4 GB / 8.6 GB · Elapsed: 00:12 · ETA: 01:20`.
    - **Worker Rows Container** (`QVBoxLayout` containing up to 4 worker slot rows):
      - Each worker slot row contains:
        - `QLabel("Worker 1:")` (fixed width `65px`, bold `#38BDF8`)
        - `QProgressBar` (height `6px`, styled cyan `#38BDF8`)
        - `QLabel("[filename] · 45% (3.2 MB/s)")` (stretch=1)
  - Dynamically show/hide worker slot rows according to `self.worker_slider.value()` during download.
  - Reset and hide worker bars when download completes, cancels, or is idle.
- In `_on_download_progress()`:
  - Route per-worker download events (`worker_id`, `filename`, `percent`, `speed_mbps`) directly to that worker's `QProgressBar` and label.

### 4. Verification Suite
- Start a batch download of 10+ files with 2 concurrent workers:
  - Verify that 2 distinct visual worker progress bars actively fill simultaneously.
  - Hit **CANCEL / ABORT**:
    - Verify ONLY the 2 in-flight files transition to `"Aborted"`.
    - Verify all remaining files stay `"Pending"`.
    - Verify ZERO red `[ERROR]` lines appear in the console.
- Run `uv run pytest tests/unit/test_ui.py`.
- Run `uv run mypy src tests` (100% strict type safety).
- Run `uv run ruff check .`.
- Present the updated walkthrough in `.gemini/logs/task-007-zm-walkthrough.md`.