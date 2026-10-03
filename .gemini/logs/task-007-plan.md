# Implementation Plan - Task 007: PySide6 Native Desktop GUI — HikVision Downloader by Arivedha

## 1. Task Analysis & Requirements
Task 007 introduces a responsive, non-blocking native PySide6 desktop GUI for Hikvision Downloader branded as **"HikVision Downloader by Arivedha"**. The UI provides a professional operator console for CCTV retrieval with secure OS keychain credential storage, dynamic multi-camera selection with stream overrides, space pre-flight validation, asynchronous non-blocking worker threads, and live activity logging.

### Key Deliverables:
1. **`pyproject.toml` Configuration**:
   - Add `PySide6>=6.6.0` and `keyring>=24.0.0` to project dependencies.
   - Register the GUI CLI entry point:
     `hikvision-downloader-gui = "hikvision_downloader.ui.main_window:main"`
2. **Brand Assets (`src/hikvision_downloader/ui/assets/`)**:
   - `favicon.svg` & `logo.svg`: High-resolution vector CCTV and Arivedha badge icon.
   - Theme styling adhering to brand palette:
     - Flame Orange: `#F37021`
     - Teal: `#1E6B7B`
     - Deep Navy: `#1B3651`
     - Backgrounds: Dark slate `#121820` / `#1A232E`, cards `#222D3D`, borders `#2E3D52`, text `#E2E8F0`, accents `#38BDF8`, success `#10B981`, warning `#F59E0B`, error `#EF4444`.
3. **OS Keychain & Credential Store (`src/hikvision_downloader/ui/keychain.py`)**:
   - Securely save and retrieve NVR passwords using `keyring` without storing plain text on disk.
   - Support keychain service name `hikvision_downloader` with account keys `f"{host}:{port}:{username}"` and `f"{host}:{username}"`.
   - Ensure zero cleartext password logging, zero leaking in repr, and graceful fallback if keychain is inaccessible.
4. **Background Workers (`src/hikvision_downloader/ui/workers.py`)**:
   - `AuthWorker(QThread)`: Tests NVR credentials, creates authenticated session, and returns connection status.
   - `DiscoveryWorker(QThread)`: Runs `CameraDiscoveryService` dynamically over ISAPI without blocking the UI.
   - `SearchWorker(QThread)`: Queries `CMSearch` across all selected cameras and time spans, extracting metadata and segments.
   - `DownloadWorker(QThread)`: Executes `download_recordings_concurrent` across selected segments with thread-safe progress signal dispatch and cancellation.
   - All workers emit Qt signals (`signal_started`, `signal_progress`, `signal_log`, `signal_finished`, `signal_error`).
5. **UI Components & Layout (`src/hikvision_downloader/ui/`)**:
   - `models.py`: Qt table model (`RecordingsTableModel`) supporting segment selection, checkboxes, column sorting, byte formatting, and duration calculations.
   - `main_window.py`: Master `QMainWindow` layout:
     - **Top Brand & Login Header**: Arivedha logo, title "HikVision Downloader by Arivedha", live status indicator LED, Host, Port, Username, Password (masked), "Remember Password (OS Keychain)" checkbox, and "Connect / Refresh" button.
     - **Left Control Panel**:
       - Multi-camera selection list with "Select All" / "Deselect All", "Refresh Channels" button, global stream selector (HD / SD), and per-camera stream override dropdowns.
       - Investigation Date & Time Window: Defaults to yesterday's date (`date.today() - timedelta(days=1)`) and "Entire Day" (00:00:00 to 23:59:59) with custom time range support.
       - Concurrency slider (1 to 4 workers, default 2).
       - Output Directory selector (`QFileDialog`) with free disk space indicator.
       - "Search Segments" action button.
     - **Right Operational Panel**:
       - `QTableView` with segment items, duration, size, selection checkboxes, and column sorting.
       - Pre-flight validation banner: Total selected size vs. available disk space with safety check.
       - Action buttons: Prominent "START BATCH DOWNLOAD" (Flame Orange) and "CANCEL / ABORT" (Red).
       - Progress indicators: Total progress bar, instantaneous throughput (Mbps), elapsed time, dynamic ETA.
       - Live Scrolling Activity Log Console (`QPlainTextEdit`): Timestamped color-coded logs (`INFO`, `PROGRESS`, `SKIP`, `WARN`, `ERROR`, `SUCCESS`).
6. **Unit Tests (`tests/unit/test_ui.py`)**:
   - Headless unit tests for keychain storage wrappers, table models, space pre-flight validation calculations, worker signal propagation, and stream override mappings.
   - 100% offline execution with zero display server dependency.

---

## 2. Target Files & Proposed Actions

| File | Operation | Description |
|---|---|---|
| `.gemini/logs/task-007-plan.md` | Create | This execution plan for Task 007. |
| `pyproject.toml` | Modify | Add `PySide6>=6.6.0`, `keyring>=24.0.0` dependencies and `hikvision-downloader-gui` entry point. |
| `src/hikvision_downloader/ui/__init__.py` | Create | Package initialization and module exports. |
| `src/hikvision_downloader/ui/assets/logo.svg` | Create | Arivedha CCTV vector icon and logo. |
| `src/hikvision_downloader/ui/assets/favicon.svg` | Create | Favicon asset for window and taskbar icons. |
| `src/hikvision_downloader/ui/style.py` | Create | Modern dark theme QSS stylesheet adhering to Arivedha brand palette. |
| `src/hikvision_downloader/ui/keychain.py` | Create | OS keychain wrapper using `keyring` for secure password persistence. |
| `src/hikvision_downloader/ui/models.py` | Create | `RecordingsTableModel`, `CameraItemModel`, and data adapter structures. |
| `src/hikvision_downloader/ui/workers.py` | Create | `QThread` workers for non-blocking Auth, Discovery, CMSearch, and Concurrent Downloads. |
| `src/hikvision_downloader/ui/main_window.py` | Create | Main GUI window, layout orchestration, event routing, and CLI entry point `main()`. |
| `tests/unit/test_ui.py` | Create | Headless unit tests for UI models, workers, keychain, pre-flight space check, and stream overrides. |
| `.gemini/logs/task-007-walkthrough.md` | Create (Phase 2) | Walkthrough capturing implementation details, static checks, and test results. |

---

## 3. Detailed Logic & Architecture Design

### 3.1 Security & Keychain Credential Management (`src/hikvision_downloader/ui/keychain.py`)
- Service name: `hikvision_downloader`
- Functions:
  ```python
  def save_nvr_password(host: str, username: str, password: str, port: int = 80) -> bool: ...
  def get_nvr_password(host: str, username: str, port: int = 80) -> str | None: ...
  def delete_nvr_password(host: str, username: str, port: int = 80) -> bool: ...
  ```
- Uses `keyring.set_password`, `keyring.get_password`, `keyring.delete_password`.
- Wraps keychain calls in `try...except (keyring.errors.KeyringError, Exception)` to handle headless or locked keyring environments without crashing.
- Never logs or exposes retrieved passwords.

### 3.2 Signal-Driven Worker Architecture (`src/hikvision_downloader/ui/workers.py`)
- **`AuthWorker(QThread)`**:
  - Inputs: `host`, `port`, `username`, `password`, `auth_type`.
  - Signals: `signal_finished(bool, str, object)`, `signal_log(str, str)`.
  - Logic: Creates session via `create_authenticated_session(...)`, verifies connectivity with quick test request, and passes session back to main thread.
- **`DiscoveryWorker(QThread)`**:
  - Inputs: `session`, `host`, `port`, `force_refresh`.
  - Signals: `signal_cameras(dict)`, `signal_error(str)`, `signal_log(str, str)`.
  - Logic: Executes `CameraDiscoveryService.get_cameras(...)`.
- **`SearchWorker(QThread)`**:
  - Inputs: `session`, `host`, `port`, list of `(camera, track_id)`, `target_date`, `time_start`, `time_end`.
  - Signals: `signal_recordings_found(object, list)`, `signal_progress(int, int)`, `signal_finished(int)`, `signal_error(str)`, `signal_log(str, str)`.
  - Logic: Executes `get_all_recordings(...)` across selected camera tracks with progress notifications.
- **`DownloadWorker(QThread)`**:
  - Inputs: `session`, `host`, `port`, list of `(Recording, TrackId, Path, int, int)`, `max_workers`, `output_dir`.
  - Signals: `signal_progress(DownloadProgress)`, `signal_file_completed(str, bool)`, `signal_finished(DownloadResult)`, `signal_error(str)`, `signal_log(str, str)`.
  - Logic: Coordinates batch downloading via `download_recordings_concurrent`, translating progress callbacks into thread-safe Qt signals and supporting cancellation through `threading.Event()`.

### 3.3 Recordings Table Model (`src/hikvision_downloader/ui/models.py`)
- Inherits from `QAbstractTableModel`.
- Columns:
  1. `Select` (Checkbox, `Qt.ItemIsUserCheckable`)
  2. `Camera` (`D1 MainGate`)
  3. `Stream` (`HD` / `SD`)
  4. `File Name` (`ch01_20261002_000000.mp4`)
  5. `Start Time` (`YYYY-MM-DD HH:MM:SS`)
  6. `End Time` (`YYYY-MM-DD HH:MM:SS`)
  7. `Size` (Formatted `124.5 MB`)
  8. `Status` (`Pending` / `Downloading` / `Completed` / `Skipped` / `Failed`)
- Implements `headerData`, `data`, `setData`, `flags`, sorting via `sort()`, selection toggling (`select_all`, `deselect_all`, `select_range`), and total size calculation for checked items.

### 3.4 Pre-flight Space Validation & Disk Safety
- Formula:
  ```python
  def check_disk_space(output_dir: Path, required_bytes: int) -> tuple[bool, int, int]:
      usage = shutil.disk_usage(output_dir)
      free_bytes = usage.free
      has_space = free_bytes >= (required_bytes + 100 * 1024 * 1024)  # 100MB safety buffer
      return has_space, required_bytes, free_bytes
  ```
- The UI displays an alert banner if `required_bytes > free_bytes` and prompts for user confirmation before starting batch download.

### 3.5 Operator Console Main Window (`src/hikvision_downloader/ui/main_window.py`)
- **Header Toolbar**:
  - Logo icon + App Title + Version badge.
  - Connection form: Host, Port, Username, Password, Remember Checkbox, Connect button.
  - Status Pill: `Disconnected` (Gray), `Connecting` (Yellow), `Connected` (Green), `Error` (Red).
- **Left Sidebar**:
  - Camera list widget: Checkboxes for each camera with stream selection combo (`HD (Main)`, `SD (Sub)`).
  - Quick action buttons: "Select All Cameras", "Deselect All", "Refresh Channels".
  - Date & Time: `QDateEdit` defaulting to yesterday (`QDate.currentDate().addDays(-1)`), checkbox for "Full Day (00:00:00 - 23:59:59)" or custom `QTimeEdit` range.
  - Options: Worker Concurrency Slider (`1` to `4`, default `2`), Output Directory Selector with Browse button.
  - Action: "Search Recordings" Button (Teal accent).
- **Right Main Panel**:
  - Recordings `QTableView` with checkbox header and quick count summary (e.g. `96 segments found, 96 selected (14.2 GB)`).
  - Disk space status pill (`Free: 128.4 GB / Required: 14.2 GB [OK]`).
  - Action Bar: Large "START BATCH DOWNLOAD" button (`#F37021`) + "CANCEL / ABORT" button (`#EF4444`).
  - Progress Section:
    - Overall batch progress bar (`QProgressBar`).
    - Speed readout (`24.5 Mbps`), Elapsed Time, Remaining ETA.
  - Live Console Log (`QPlainTextEdit`):
    - Monospace font, auto-scroll, timestamped lines, colored tags (`[INFO]`, `[DOWNLOAD]`, `[SKIP]`, `[SUCCESS]`, `[ERROR]`).

---

## 4. Verification and Testing Plan

### 4.1 Unit Tests (`tests/unit/test_ui.py`)
1. **OS Keychain Operations**:
   - Test `save_nvr_password`, `get_nvr_password`, `delete_nvr_password` using mocked `keyring`.
   - Test graceful exception handling when keyring backend is unavailable.
2. **Recordings Table Model**:
   - Test item insertion, data retrieval, column headers, and checkbox toggle.
   - Test total size calculation of checked vs unchecked recordings.
   - Test selection helpers (`select_all`, `deselect_all`, `toggle_item`).
3. **Space Pre-Flight Calculation**:
   - Test `check_disk_space` with sufficient space and insufficient space.
   - Verify safety buffer calculations.
4. **Camera Item & Stream Override Mappings**:
   - Verify stream override resolution (HD -> main_track, SD -> sub_track).
5. **Worker Signals & Thread Execution**:
   - Test `AuthWorker`, `DiscoveryWorker`, `SearchWorker`, `DownloadWorker` signal emission using headless mock session.
6. **Headless Execution Guard**:
   - Set `QT_QPA_PLATFORM=offscreen` during test execution to guarantee zero display server dependency.

### 4.2 Static Checks & Regressions
- Run `uv run pytest` across all unit, functional, and integration tests.
- Run `uv run mypy src tests` to verify 100% strict type annotations.
- Run `uv run ruff check .` and `uv run ruff format --check .`.

---

## 5. Invariant Checklist
- [x] Strict presentation decoupling: `src/hikvision_downloader/core/` does NOT import `PySide6`.
- [x] 100% type annotations across all new code in `src/` (zero bare `Any`).
- [x] Passwords must NEVER be logged, displayed in cleartext, or leaked in error messages; `keyring` used for secure persistence.
- [x] Stop at Step 5 for explicit user approval before making any code modifications.
