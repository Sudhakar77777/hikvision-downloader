# Task 007-ZE Implementation Plan: Critical UI Refactor & Search Optimization

## Objectives
Execute the comprehensive UI refactoring specified in `.gemini/tasks/007-ze-ui-bugs4.md`:
1. Root-cause elimination of macOS/cross-platform Qt font warnings (`qt.qpa.fonts`) via native `QFontDatabase.systemFont()` programmatic font resolution.
2. Global stripping of borders and backgrounds on `QLabel` elements to ensure all textual labels render flat.
3. Top connection bar symmetry, compact inputs (`Host: 120px`, `Port: 50px`, `User: 90px`, `Password: 90px`), dynamic color-coded Connect/Disconnect button (`#1E6B7B` teal vs `#DC2626` red), compact status badge (`padding: 2px 6px; font-size: 10px;`), and `32x26px` theme toggle.
4. Simplified stream selection: eliminate per-camera override radios; provide single unified `Stream Quality` dropdown beneath camera checklist with dynamic track availability detection.
5. Symmetrical time window row (`From: [HH]:[MM]  To: [HH]:[MM]`).
6. Workflow panel reorganization:
   - **Left Panel (Input & Search)**: Camera Channels + Stream Quality + Time Window + Pinned `[ 🔍 SEARCH RECORDINGS ]` button.
   - **Right Panel (Results & Actions)**: Table + Compact Download Settings Card (Output Dir + Workers + CSV checkbox) + Batch Download Actions + Console with integrated progress header.
7. Search execution verification and end-to-end data flow into `RecordingsTableModel`.
8. Complete validation suite passing 100% (`pytest`, `mypy`, `ruff`).

---

## Technical Strategy & Architecture

### Phase 1: Native System Font Resolution & Style Sheet Refinement
- In `src/hikvision_downloader/ui/style.py`:
  - Completely strip all `font-family` properties from `DARK_THEME_QSS` and `LIGHT_THEME_QSS`.
  - Add global flat label rule:
    ```css
    QLabel {
        background: transparent;
        border: none;
        padding: 0px;
    }
    ```
  - Define explicit styles for bordered badges: `#statusBadge`, `#spaceBadge`.
  - Style `#connectBtn[connected="true"]` (`background-color: #DC2626; color: #FFFFFF;`) and `#connectBtn[connected="false"]` (`background-color: #1E6B7B; color: #FFFFFF;`).
  - Style `#searchBtn` (`background-color: #1E6B7B; color: #FFFFFF; font-weight: bold; padding: 8px 16px; border-radius: 6px;`).
  - Style `#downloadBtn` (`background-color: #F37021; color: #FFFFFF; font-weight: bold; padding: 8px 16px; border-radius: 6px;`).
- In `src/hikvision_downloader/ui/main_window.py` (and GUI startup):
  - Programmatically apply `QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)` to `QApplication.setFont()`.
  - Programmatically apply `QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)` to `self.console_log.setFont()`.

### Phase 2: Top Connection Bar Redesign
- Reconfigure top header inputs with exact constraints:
  - `host_input`: `setMaximumWidth(120)`
  - `port_input`: `setFixedWidth(50)`, centered, no buttons
  - `user_input`: `setMaximumWidth(90)`
  - `password_input`: `setMaximumWidth(90)`
  - `remember_cb`: `QCheckBox("Save in Keychain")`
  - `connect_btn`: `QPushButton("Connect")` with dynamic stylesheet toggle between `#1E6B7B` (Connect) and `#DC2626` (Disconnect)
  - `status_badge`: Compact pill (`font-size: 10px; padding: 2px 6px; border-radius: 8px;`)
  - `theme_btn`: `setFixedSize(32, 26)` icon toggle (`☀️`/`🌙`)

### Phase 3: Left Panel (Source & Time & Search Action)
- Stream Selection:
  - Remove `stream_btn_group`, `rb_global_stream`, and `rb_override_stream`.
  - Simplify `CameraRowWidget` to contain `QCheckBox` and `camera` metadata.
  - Position unified `Stream Quality` `QComboBox` (`self.stream_combo`) beneath the camera scroll area.
  - When discovery finishes, inspect camera tracks: populate `["HD (Main Stream)"]` or `["HD (Main Stream)", "SD (Sub Stream)"]` dynamically.
- Time Window:
  - Symmetrical row: `From:` `[HH]` `:` `[MM]` `To:` `[HH]` `:` `[MM]` (compact 56px combo boxes, 10px centered colons).
  - 4 uniform preset buttons (`AM (08-12)`, `NOON (12-18)`, `PM (18-24)`, `FULL (00-24)`).
- Search Action:
  - Large pinned `[ 🔍 SEARCH RECORDINGS ]` button at the bottom of the left panel.
  - Remove all download settings from the left panel.

### Phase 4: Right Panel (Results, Download Settings, Actions & Log Console)
- Top: Segments Table (`summary_label`, `[Select All]`, `[Clear]`, `table_view`).
- Middle: **Download Settings Frame** (2 compact lines):
  - Line 1: `Output Directory: [ path... ] [📂 (32x26px)] [ Free Space Pill ]`
  - Line 2: `Concurrent Workers: [ Slider 1-4 ] [✓] Generate recording-list.csv manifest`
- Action Row:
  - Primary: `[ ⬇ START BATCH DOWNLOAD ]` (`#F37021`) + `[ ✕ CANCEL / ABORT ]` (`#DC2626`).
- Bottom: **Activity Console & Header Progress Bar**:
  - Console header with integrated status: `Progress: [ Idle | 0.0% | 0.0 MB/s | ETA: --:-- ]` and `[ Clear Console ]` button.
  - Console text box with native monospace font.

### Phase 5: Search Worker & Data Pipeline Integration
- Validate `SearchWorker` connection parameters, XML payload creation, and pagination loop.
- Connect `signal_camera_recordings` to `_on_camera_recordings_found` and update `_table_model` cleanly.
- Ensure logging output reflects querying progress and discovered counts accurately.

### Phase 6: Test Suite Updates & Verification
- Update `tests/unit/test_ui.py` to match the new UI component hierarchy and properties.
- Run `uv run pytest tests/unit/test_ui.py` and `uv run pytest tests/unit tests/functional`.
- Run `uv run mypy src tests` (zero type errors).
- Run `uv run ruff check .` and `uv run ruff format --check .`.
- Write detailed walkthrough to `.gemini/logs/task-007-ze-walkthrough.md`.

---

## Verification Plan

### Automated Tests
1. `uv run pytest tests/unit/test_ui.py` (verify UI components, workers, signals, search flow).
2. `uv run pytest tests/unit tests/functional` (full regression test suite).
3. `uv run mypy src tests` (strict type analysis).
4. `uv run ruff check .` (linter checks).
5. `uv run ruff format --check .` (formatting checks).

### Manual Verification
- Launch application headless/onscreen and verify zero `qt.qpa.fonts` warnings on stderr.
- Verify left panel minimum width and non-collapsible splitter.
- Verify Connect/Disconnect state changes and colors.
- Verify Search populates segments table and enables Download button.
