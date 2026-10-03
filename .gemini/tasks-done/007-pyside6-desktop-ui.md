# Task 007: PySide6 Native Desktop GUI — HikVision Downloader by Arivedha

## Objective
Implement a responsive, non-blocking native PySide6 desktop GUI for Hikvision Downloader branded as "HikVision Downloader by Arivedha". Features include top-bar NVR authentication with OS keychain storage (`keyring`), multi-camera selection with per-camera stream overrides, default "yesterday full-day" time window, space pre-flight validation, a prominent start action, a live scrolling Windows-style activity log console, and brand assets integration (`favicon.svg`).

## Target Changes
1. **`pyproject.toml`**:
   - Add `PySide6>=6.6.0` and `keyring>=24.0.0` to dependencies.
   - Register GUI entry point: `hikvision-downloader-gui = "hikvision_downloader.ui.main_window:main"`.
2. **Assets (`src/hikvision_downloader/ui/assets/`)**:
   - Embed `logo.svg` / `favicon.svg` for window and taskbar icons.
   - Apply brand palette: Flame Orange (`#F37021`), Teal (`#1E6B7B`), and Deep Navy (`#1B3651`).
3. **Background Workers (`src/hikvision_downloader/ui/workers.py`)**:
   - `QThread` workers for Login/Auth, Multi-Camera ISAPI Discovery, CMSearch querying across cameras, and Concurrent Batch Downloading.
   - Signal-driven architecture (`signal_progress`, `signal_log`, `signal_finished`, `signal_error`) ensuring the Qt main event loop runs at 60 FPS without blocking.
4. **Desktop Layout (`src/hikvision_downloader/ui/`)**:
   - `main_window.py`: Master window orchestrating the operator console.
   - **Top Brand & Login Header**: Arivedha logo/icon, title "HikVision Downloader by Arivedha", live connection indicator, Host, Port, Username, Password (masked), and "Remember in OS Keychain" checkbox.
   - **Left Control Panel**:
     - NVR hardware & storage status.
     - Multi-camera checklist with "Select All", "Refresh Channels" (`clear_cache()`), global stream selector, and per-camera stream overrides (HD/SD).
     - Investigation time window defaulting to yesterday's date and "Entire Day" (00:00:00 - 23:59:59).
     - Worker concurrency slider (1–4) and output directory selector.
     - "Search Segments" action button.
   - **Right Operational Panel**:
     - Discovered segments `QTableView` with multi-select checkboxes, column sorting, and metadata totals (estimated total size vs. available disk space).
     - Primary Action Bar: Large "START BATCH DOWNLOAD" button and "CANCEL / ABORT" button.
     - Live Event Log Console (`QPlainTextEdit`): Timestamped scrolling terminal log detailing worker events, chunk streaming, file skips, and cancellations.
     - Overall progress bar, instantaneous Mbps indicator, and dynamic ETA display.
5. **Tests (`tests/unit/test_ui.py`)**:
   - Headless unit tests validating worker thread signals, space validation calculations, stream override mappings, and model adapters.

## Strict Invariants
- Adhere strictly to `.gemini/rules/1-workflow.md`, `2-security.md`, `3-design.md`, and `4-coding-standards.md`.
- Strict presentation decoupling: `core/` must NEVER import `PySide6`.
- 100% type annotations across all new code (zero bare `Any`).
- Passwords must NEVER be logged or shown in cleartext; OS credential storage must strictly use `keyring`.
- Save Phase 1 plan to `.gemini/logs/task-007-plan.md` and stop for approval.
- Save Phase 2 walkthrough to `.gemini/logs/task-007-walkthrough.md`.