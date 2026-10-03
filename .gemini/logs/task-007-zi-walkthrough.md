# Task 007-ZI Walkthrough: Camera Name Exactness, Table Column Symmetry, Disconnect Purge & Interactive Profiles

## Overview
Task 007-ZI delivered critical UI and state architecture overhauls for the desktop application:
1. **Real NVR Camera Name Exactness**:
   - Removed all artificial "CH01", "CH02", etc. string manipulations and prefixes.
   - Preserved exact camera names as returned from NVR/ISAPI discovery (`camera.name`, e.g., `D1 MainGate`, `D4 FirstFL`, `MainGate`).
2. **Exact Visual & Column Symmetry Across Both Tables**:
   - Hidden native vertical headers on BOTH Left (Cameras) and Right (Recordings) tables (`table.verticalHeader().setVisible(False)`).
   - Matched row heights across both tables (`table.verticalHeader().setDefaultSectionSize(22)`).
   - Standardized **Column 0** on both tables as selection checkbox `[✓]` (width `34px`, centered).
   - Standardized **Column 1** on both tables as row number `#` (width `40px`, centered text: `1`, `2`, `3`...).
   - Left Table Columns: `[✓]` | `#` | `Camera Name` | `Hardware Model`.
   - Right Table Columns: `[✓]` | `#` | `Camera` | `Stream` | `File Name` | `Start Time` | `End Time` | `Size` | `Status`.
3. **Complete State Purge on Disconnect**:
   - Cleanly stops active workers and clears session objects (`_session = None`, `_discovered_cameras`, `_discovered_dates`, `_device_info`).
   - Clears Left Camera Table and restores the centered placeholder label: `"No cameras discovered. Click 'Connect' to discover cameras."` via `QStackedWidget`.
   - Clears Right Recordings Table (0 rows) and resets summary: `"0 segments discovered (0 B) | 0 selected (0 B)"`.
   - Disables action buttons: `START BATCH DOWNLOAD`, `SEARCH RECORDINGS`, and `CANCEL / ABORT`.
   - Clears and disables the `Stream Quality` dropdown.
   - Clears `Password:` input field (`self.password_input.clear()`).
   - Logs `[INFO] Session disconnected. Ready.` to the live console.
4. **Interactive OS Keychain & Saved NVR Profiles**:
   - Created `src/hikvision_downloader/ui/profiles.py` persisting known `(host, port, username)` tuples in `~/.hikvision-downloader/profiles.json`.
   - Converted `self.host_input` and `self.user_input` to editable `ProfileComboBox` widgets populated from saved profiles and `.env` defaults.
   - Added reactive keychain queries on host/user changes to auto-populate passwords with structured logging.
   - Automatically saves successful connection profiles and persists passwords to OS Keychain when "Save in Keychain" is checked.
   - Handled all keychain errors cleanly with explicit `[ERROR] OS Keychain access failed: <details>` console logging.

---

## Key Changes Implemented

### 1. NVR Profiles Storage Module ([profiles.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/profiles.py))
- Created Pydantic `NvrProfile` model with `host`, `port`, `username`, and `last_used` epoch timestamp.
- Implemented `load_profiles()`, `save_profile()`, `delete_profile()`, `get_saved_hosts()`, and `get_saved_usernames()`.
- Guaranteed atomic history maintenance (capped at 50 profiles, sorted by most recently used).
- Exported in `src/hikvision_downloader/ui/__init__.py`.

### 2. Camera & Recording Models ([models.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/models.py))
- `CameraItem.display_name`: Returns `self.camera.name` directly (no artificial prefixing).
- `CamerasTableModel`:
  - `COL_CHECK = 0` (`""`, 34px)
  - `COL_NUM = 1` (`"#"`, 40px, centered `#64748B`)
  - `COL_NAME = 2` (`"Camera Name"`)
  - `COL_MODEL = 3` (`"Hardware Model"`, `#94A3B8`)
- `RecordingsTableModel`:
  - Upgraded to 9 columns for visual symmetry with the camera table:
    - `COL_CHECK = 0` (`""`, 34px)
    - `COL_NUM = 1` (`"#"`, 40px, centered `#64748B`)
    - `COL_CAMERA = 2` (`"Camera"`, displays exact `item.camera.name`)
    - `COL_STREAM = 3` (`"Stream"`, centered HD/SD)
    - `COL_FILENAME = 4` (`"File Name"`)
    - `COL_START = 5` (`"Start Time"`)
    - `COL_END = 6` (`"End Time"`)
    - `COL_SIZE = 7` (`"Size"`, right-aligned)
    - `COL_STATUS = 8` (`"Status"`, colored pill/text)
  - Sorting and data retrieval updated across all 9 columns.

### 3. MainWindow UI Overhaul ([main_window.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py))
- **Header Profile ComboBoxes**:
  - `ProfileComboBox(QComboBox)` supporting text/editing signals and `.text()` / `.setText()` ergonomic access.
  - Initialized and populated via `_populate_profile_combos()`.
  - Wired `_on_host_combo_changed` and `_on_user_combo_changed` to reactive keychain lookup `_auto_lookup_keychain()`.
- **Camera Stack & Placeholder**:
  - Implemented `QStackedWidget` containing `cameras_placeholder_label` (page 0) and `cameras_table` (page 1).
  - Toggles to table upon discovery, and reverts to placeholder upon disconnect.
- **Table Visual Symmetry**:
  - Both tables have `verticalHeader().setVisible(False)` and `verticalHeader().setDefaultSectionSize(22)`.
  - Column widths configured with fixed `34px` for `COL_CHECK` and `40px` for `COL_NUM`.
- **Full Disconnect Purge**:
  - `_disconnect_session()` cancels workers, clears models, resets summary text, resets progress bars, disables buttons (`search_btn`, `start_download_btn`, `stream_combo`), clears `password_input`, restores the placeholder, and logs `"Session disconnected. Ready."`.

### 4. Unit & Regression Tests ([test_ui.py](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/tests/unit/test_ui.py))
- Added `test_profiles_load_save_delete` and `test_profiles_corrupted_handling`.
- Updated `test_cameras_table_model_operations` and `test_table_model_operations` to verify 9-column symmetry, exact camera names, row numbers, and sorting.
- Updated `test_main_window_instantiation` and `test_disconnect_session_complete_purge` to verify placeholder state, button disabling, and password clearing.

---

## Verification Results

### 1. UI Unit Tests
```
$ uv run pytest tests/unit/test_ui.py
============================= test session starts ==============================
platform darwin -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /Volumes/MinionDev/Workspace/CCTV/hikvision-downloader
configfile: pyproject.toml
plugins: mock-3.16.0
collected 23 items

tests/unit/test_ui.py .......................                            [100%]

============================== 23 passed in 0.67s ==============================
```

### 2. Static Type Checking (`mypy`)
```
$ uv run mypy src tests
Success: no issues found in 41 source files
```

### 3. Linting & Coding Standards (`ruff`)
```
$ uv run ruff check .
All checks passed!
```

### 4. Full Test Suite
```
$ uv run pytest
================== 157 passed, 1 skipped in 72.27s (0:01:12) ===================
```
