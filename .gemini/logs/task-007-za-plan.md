# Implementation Plan - Task 007-ZA: PySide6 Desktop UI Polishing & Ergonomic Enhancements

## 1. Task Analysis & Requirements
This task addresses UI ergonomic issues, window sizing/layout truncation, stream selection ambiguity, calendar legibility with recorded dates discovery, time picker ergonomics, corporate branding restructuring, and light/dark theme switching for the Hikvision Downloader desktop GUI.

### Key Deliverables:
1. **Window Sizing & Layout Geometry ([`src/hikvision_downloader/ui/main_window.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py))**:
   - Set default window dimensions to 1320x880 with a minimum size of 1150x750.
   - Adjust stretch factors and layout padding:
     - Top connection bar: Provide adequate minimum widths and horizontal spacing for Host (`150px`), Port (`75px`), User (`110px`), Password (`130px`), "Save in Keychain" checkbox, and connection status pill so nothing is truncated or cramped against the margins.
     - Left control panel: Ensure "Refresh Channels" button displays full text ("Refresh Channels"), output directory Browse button displays full text ("Browse...").
     - Right operational panel: Generous spacing between summary text and range selection controls ("Select Range", "Select All", "Clear").
2. **Corporate Branding & Logo Restructuring**:
   - Header Bar: Focus on product identity with application icon and clean title `"HikVision Downloader"`.
   - Dedicated Footer Bar: Move Arivedha corporate branding to a dedicated footer frame at the bottom of the window:
     - Embed the vector lamp/flame mark from `assets/favicon.svg`.
     - Display `"Powered by Arivedha Solutions"` with subtle version badge.
3. **Default Output Directory Resolution**:
   - Priority 1: `os.getenv("HIKVISION_OUTPUT_DIR")` if set and non-empty.
   - Priority 2 (Default fallback): `Path.home() / "Downloads" / "HikvisionArchive"`.
   - Line edit displays the full resolved path with hover tooltip and allows expanding.
4. **Stream Selection Radio Toggle**:
   - Replace ambiguous global vs. per-camera dropdowns with a clear radio mode toggle:
     - `(●) Global Stream (All Cameras)` [Default]
     - `( ) Per-Camera Override`
   - **Global Stream mode**: Display only top global stream combo (`HD (Main Stream)` / `SD (Sub Stream)`). Hide per-camera stream dropdowns next to camera rows for a clean, wide camera list.
   - **Per-Camera Override mode**: Reveal stream dropdowns next to each camera row (defaulting to HD). If a camera only has 1 track, display a static text badge (`HD`) instead of a dropdown.
5. **Calendar Legibility, Recorded Dates Discovery & Theme Switching**:
   - **Theme Switching**: Add a Dark/Light Mode toggle in the top toolbar with complete QSS stylesheets (`DARK_THEME_QSS` and `LIGHT_THEME_QSS` in [`style.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/style.py)).
   - **QCalendarWidget Styling**: Style navigation bar buttons (`<` and `>`), month/year menus, header labels, and date grid with high-contrast text and arrows in both dark and light modes.
   - **Recorded Dates Highlighting**:
     - Implement `DatesWorker(QThread)` in [`workers.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/workers.py) querying `discover_available_dates()` over ISAPI in the background upon successful NVR connection.
     - Highlight confirmed recording dates in `QCalendarWidget` using `QTextCharFormat` (Flame Orange accent background/border and tooltip `"Footage Available"`), so operators immediately see available recording days.
6. **Time Range Selection Ergonomics**:
   - Replace micro-spinners with clean `HH:MM` combo boxes:
     - From: `[Hour 00-23]` : `[Minute 00, 15, 30, 45]`
     - To: `[Hour 00-23]` : `[Minute 00, 15, 30, 45, 59]`
   - Quick preset buttons:
     - `"Morning (08:00 - 12:00)"`
     - `"Afternoon (12:00 - 18:00)"`
     - `"Evening (18:00 - 23:59)"`
     - `"Full Day (00:00 - 23:59)"`
   - Retain `"Full Day (00:00 - 23:59)"` checkbox (checked by default), disabling custom time inputs until unchecked.
7. **Headless Unit Tests & Quality Verification**:
   - Add unit tests in [`tests/unit/test_ui.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/tests/unit/test_ui.py) for output directory resolution, stream mode switching, `DatesWorker` signal emission, calendar highlighting format, and theme switching.
   - Verify with `uv run pytest`, `uv run mypy src tests`, and `uv run ruff check .`.

---

## 2. Target Files & Proposed Actions

| File | Operation | Description |
|---|---|---|
| `.gemini/logs/task-007-za-plan.md` | Create | This execution plan for Task 007-ZA. |
| `src/hikvision_downloader/ui/style.py` | Modify | Add `LIGHT_THEME_QSS`, enhance `DARK_THEME_QSS` with `QCalendarWidget` contrast, stream radio buttons, footer frame, and theme switch styling. |
| `src/hikvision_downloader/ui/workers.py` | Modify | Add `DatesWorker(QThread)` for non-blocking ISAPI daily distribution discovery. |
| `src/hikvision_downloader/ui/main_window.py` | Modify | Implement 1320x880 layout, top header with theme switch, footer branding frame, output path resolution (`HIKVISION_OUTPUT_DIR` / `~/Downloads/HikvisionArchive`), stream selection radio toggle, `QCalendarWidget` recorded dates highlighting, and `HH:MM` time presets. |
| `tests/unit/test_ui.py` | Modify | Add unit tests for `DatesWorker`, stream selection toggle mode, default output path, and theme switcher. |
| `.gemini/logs/task-007-za-walkthrough.md` | Create (Phase 2) | Walkthrough documenting all fixes, test results, and visual verification. |

---

## 3. Detailed Logic & Architecture Design

### 3.1 Output Directory Resolution
```python
def resolve_default_output_dir() -> Path:
    env_dir = os.getenv("HIKVISION_OUTPUT_DIR")
    if env_dir and env_dir.strip():
        return Path(env_dir.strip()).expanduser().resolve()
    return Path.home() / "Downloads" / "HikvisionArchive"
```

### 3.2 Stream Selection Radio Mode Logic
- `CameraRowWidget` contains:
  - `checkbox`: `QCheckBox` with camera display name.
  - `stream_combo`: `QComboBox` (`HD (Main)`, `SD (Sub)`) or `QLabel` (`HD`) if only 1 track.
  - Method `set_override_mode(enabled: bool)`: Shows or hides `stream_combo`.
- `MainWindow`:
  - Radio buttons: `rb_global_stream` vs `rb_override_stream`.
  - When `rb_global_stream.isChecked()`:
    - Global combo is enabled.
    - Each `CameraRowWidget.set_override_mode(False)` hides row combo.
    - Active stream for all cameras = Global combo value.
  - When `rb_override_stream.isChecked()`:
    - Global combo is disabled.
    - Each `CameraRowWidget.set_override_mode(True)` shows row combo.
    - Active stream for each camera = row's individual combo selection.

### 3.3 Recorded Dates Highlighting (`DatesWorker`)
- `DatesWorker(QThread)`:
  - Calls `discover_available_dates(session, host, discovery_track_id=TrackId(101))`.
  - Emits `signal_dates(dict[tuple[int, int], list[RecordingDate]])`.
- In `MainWindow._on_dates_discovered(dates_dict)`:
  - Iterates over all discovered `RecordingDate` objects.
  - Constructs `QTextCharFormat`:
    - Background: Teal (`#1E6B7B`) or Flame Orange (`#F37021`)
    - Foreground: White (`#FFFFFF`)
    - Font weight: Bold
    - Tooltip: `"Footage Available"`
  - Applies to `QCalendarWidget.setDateTextFormat(QDate(year, month, day), format)`.

### 3.4 Ergonomic Time Range Dropdowns & Presets
- Start Hour: `QComboBox` ("00" to "23")
- Start Minute: `QComboBox` ("00", "15", "30", "45")
- End Hour: `QComboBox` ("00" to "23")
- End Minute: `QComboBox` ("00", "15", "30", "45", "59")
- Quick preset buttons:
  - `Morning`: Set From `08:00`, To `12:00`, uncheck Full Day.
  - `Afternoon`: Set From `12:00`, To `18:00`, uncheck Full Day.
  - `Evening`: Set From `18:00`, To `23:59`, uncheck Full Day.
  - `Full Day`: Check Full Day checkbox (00:00 to 23:59).

---

## 4. Verification and Testing Plan

### 4.1 Unit Tests (`tests/unit/test_ui.py`)
1. **Output Directory Resolution**:
   - Verify `HIKVISION_OUTPUT_DIR` environment variable override.
   - Verify fallback to `~/Downloads/HikvisionArchive`.
2. **Stream Mode Toggle**:
   - Test global stream mode hides per-camera dropdowns and uses global selection.
   - Test per-camera override mode enables individual dropdowns.
3. **DatesWorker & Calendar Highlighting**:
   - Mock `discover_available_dates()` and test signal emission and calendar cell formatting.
4. **Theme Switcher**:
   - Test switching between Dark and Light stylesheets.
5. **Time Preset Actions**:
   - Test preset clicks update hour/minute dropdowns.

### 4.2 Static Checks & Regressions
- Run `uv run pytest` across all 148+ test cases.
- Run `uv run mypy src tests` (100% strict typing).
- Run `uv run ruff check .` and `uv run ruff format --check .`.

---

## 5. Invariant Checklist
- [x] Strict presentation decoupling: `src/hikvision_downloader/core/` does NOT import `PySide6`.
- [x] 100% type annotations across all new code (zero bare `Any`).
- [x] Stop at Step 5 for explicit user approval before making any code modifications.
