# Task 007-ZG Walkthrough: Critical UI Refactor, 3-Tier Console, Complete Purge, Keychain Auto-Fill & Visual Refinements

## Overview
Task 007-ZG executed major UI refactorings and user interaction polish across the Hikvision Downloader desktop interface (`src/hikvision_downloader/ui/`):
- Embedded symmetrical section headers into Left and Right card frames.
- Raised window launch resolution and camera scroll minimum height (`455px`).
- Aligned connection status badge (`28px`) and theme switcher button (`36x28px`).
- Implemented complete session purge on disconnect with camera row deletion and empty placeholder re-creation.
- Restructured Live Console into a 3-tier layout featuring a dedicated progress bar (`10px`, `4px` radius) and detailed telemetry readout.
- Added reactive OS Keychain credential retrieval on host/username field edits with visual cue tooltips (`🔑 Loaded from OS Keychain`).
- Tightened Left Panel camera rows vertical padding and added channel numbers (`CH01`, `CH02`) plus hardware model badges on the right column.
- Relocated segment counter summary bar directly below the recordings table view.
- Added table view vertical row numbers (`1, 2, 3...`) and enlarged table column header font size (`13px`, `700` weight).
- Overhauled Light Mode with an eye-friendly, balanced slate and off-white grey color palette.

---

## Changes Implemented

### 1. Window Geometry & Splitter Stability ([main_window.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py))
- Increased default launch geometry to `1340x920` (bounded by primary screen geometry up to `1600x1050`) with minimum size `1200x820`.
- Ensured Left Panel minimum width remains `410px`.
- Retained Camera scroll area `minimumHeight=455px` as configured.

### 2. Section Headers & Left/Right Card Symmetrical Structure ([main_window.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py))
- Replaced floating `QGroupBox` elements in the Left Panel with `QFrame` (`cardFrame`), providing visual symmetry with the Right Panel cards.
- **Left Card 1 (Top)**: Embedded flat header `QLabel("CAMERA CHANNELS & STREAM")` (`font-size: 11px; font-weight: bold; color: #38BDF8;`).
- Added explicit `10px` vertical spacing above the `Stream Quality:` dropdown.
- **Left Card 2 (Bottom)**: Embedded flat header `QLabel("RECORDING TIME WINDOW")` (`font-size: 11px; font-weight: bold; color: #38BDF8;`).

### 3. Top Connection Bar Alignment ([main_window.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py), [style.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/style.py))
- Aligned `status_badge` and `theme_btn` vertically in `headerFrame` with `Qt.AlignmentFlag.AlignVCenter`.
- `status_badge`: Fixed height `28px`, updated styling `padding: 2px 8px`, `border-radius: 6px`, `font-size: 11px`.
- `theme_btn`: Fixed size `36x28px`, centered theme icon (`☀️` / `🌙`).

### 4. Complete Session Purge on Disconnect ([main_window.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py))
- On disconnect, completely iterate through and destroy all `CameraRowWidget` children from `camera_list_layout`.
- Re-create and show the placeholder label `"No cameras discovered. Click 'Connect' to discover channels."`.
- Reset `RecordingsTableModel` to 0 rows.
- Reset segment counter text to `"0 segments discovered (0 B) | 0 selected (0 B)"`.
- Reset Stream Quality dropdown back to its default state (`HD (Main Stream)`).
- Reset progress bar to `0%` and status readout to `"[ 0% ]  Idle  |  0.0 Mbps  |  Elapsed: 00:00  |  ETA: --:--"`
- Revert footer device label strictly to `"Disconnected · Ready"`.

### 5. Live Console 3-Tier Hierarchy & Progress Bar ([main_window.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py), [style.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/style.py))
- **Tier 1 (Header Line)**: Flat section title `[ LIVE CONSOLE ]` on left, `[ Clear ]` button on far right (`setFixedHeight(24)`).
- **Tier 2 (Dedicated Status & Progress Bar Line)**: Sits directly beneath header line across full card width:
  - Left: Styled `QProgressBar` (height `10px`, radius `4px`, gradient fill `#F37021` to `#FF853E`).
  - Right: Formatted telemetry readout `progress_readout` displaying percentage, filename, speed in Mbps, elapsed time, and ETA.
- **Tier 3 (Terminal Console)**: Monospaced `QPlainTextEdit` terminal area below progress bar.

### 6. Interactive Keychain Retrieval & Reactive Auto-Fill ([main_window.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py))
- Connected `editingFinished` signal on `host_input`, `port_input`, and `user_input` to `_on_connection_field_changed()`.
- When valid credentials exist in OS Keychain for the entered host/user/port:
  - Automatically populate `password_input`.
  - Check `remember_cb` (`Save in Keychain`).
  - Set tooltip `🔑 Loaded from OS Keychain` on `password_input`.
  - Log retrieval event to live console.

### 7. Compact Camera Rows, Channel Numbers & Hardware Model ([main_window.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py), [core/models.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/core/models.py), [core/cameras.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/core/cameras.py))
- Added `model: str = ""` field to `Camera` model and populated it during ISAPI discovery.
- Tightened vertical layout margins in `CameraRowWidget` (`6, 1, 6, 1`) and `camera_list_layout` (`0, 0, 0, 0` with `spacing=2`).
- Checkbox formats channel numbers as `CH01  MainGate`.
- Display hardware model as a right-aligned badge `QLabel(camera.model)` when present.

### 8. Table Summary Bar Relocation & Vertical Row Numbers ([main_window.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py), [models.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/models.py))
- Relocated `summary_label` beneath the table view in a dedicated bottom bar.
- Enabled vertical header on `table_view` with `headerData` returning `str(section + 1)`.
- Enlarged column header font size to `13px` with `font-weight: 700`.

### 9. Eye-Friendly Light Theme ([style.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/style.py))
- Overhauled `LIGHT_THEME_QSS` replacing stark blinding whites with soft slate/off-white tones:
  - Canvas / window background: `#ECEFF3`
  - Headers & Footers: `#E2E8F0` with `#CBD5E1` borders
  - Cards: `#F8FAFC` with `#CBD5E1` borders
  - Buttons / Controls: `#E2E8F0` with `#CBD5E1` borders
  - Live Console in light mode: `#1E293B` dark terminal with crisp `#F1F5F9` text.

---

## Verification & Testing Results

### Test Suite Execution
```
$ uv run pytest tests/unit tests/functional tests/integration/test_live_nvr.py
============================= test session starts ==============================
collected 148 items

tests/unit/test_auth.py ......                                           [  4%]
tests/unit/test_camera_discovery.py ...............                      [ 14%]
tests/unit/test_cameras.py .......                                       [ 18%]
tests/unit/test_cli.py .......................................           [ 45%]
tests/unit/test_dates.py .........                                       [ 51%]
tests/unit/test_http_client.py ....                                      [ 54%]
tests/unit/test_models.py ..............                                 [ 63%]
tests/unit/test_recordings.py ..........                                 [ 70%]
tests/unit/test_ui.py ..................                                 [ 82%]
tests/functional/test_cancellation.py ....                               [ 85%]
tests/functional/test_concurrent_downloads.py .....                      [ 88%]
tests/functional/test_download_engine.py ..........                      [ 95%]
tests/integration/test_live_nvr.py .......                               [100%]

============================= 148 passed in 1.49s ==============================
```

### Static Analysis & Linter
```
$ uv run mypy src tests
Success: no issues found in 40 source files

$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
92 files already formatted
```
