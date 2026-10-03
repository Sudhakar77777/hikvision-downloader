# Task 007-ZG Implementation Plan: Critical UI Refactor, Keychain Auto-Fill & Visual Refinements

## Objectives
Execute the UI refinements across `src/hikvision_downloader/ui/` and `src/hikvision_downloader/core/` adhering strictly to `.gemini/rules/4-coding-standards.md` (100% strict type annotations):

1. **Window Geometry & Splitter Stability**:
   - In `main_window.py`:
     - Increase default launch height to `1340x920` with minimum size `1200x820` (accounting for available screen geometry).
     - Maintain Left Panel `minimumWidth=410`.
     - Increase Camera scroll area `minimumHeight` to `280px` (user set to `455px`).

2. **Section Headers: Embed Cleanly Inside Card Containers**:
   - Replace floating `QGroupBox` widgets on the Left Panel with consistent `QFrame` (`objectName="cardFrame"`).
   - **Left Card 1 (Top)**: Clean flat header inside card layout:
     `QLabel("CAMERA CHANNELS & STREAM")` styled with `font-size: 11px; font-weight: bold; color: #38BDF8; background: transparent; border: none; padding-bottom: 6px;`
   - **Left Card 2 (Bottom)**: Clean flat header inside card layout:
     `QLabel("RECORDING TIME WINDOW")` styled with matching typography.
   - Add explicit `addSpacing(10)` above `Stream Quality:` layout so it does not crowd the camera list.

3. **Top Connection Bar: Symmetrical Alignment**:
   - Ensure `status_badge` and `theme_btn` share identical fixed height (`28px`) and vertical center alignment (`Qt.AlignmentFlag.AlignVCenter`).
   - `status_badge`: `setFixedHeight(28)`, `padding: 2px 8px; font-size: 11px; border-radius: 6px;`
   - `theme_btn`: `setFixedSize(36, 28)`, clean centered icon (`☀️` / `🌙`), transparent/subtle border, zero horizontal margin clipping.

4. **Complete Session Purge on Disconnect**:
   - In `_disconnect_session()`:
     - Stop all active background workers.
     - Completely purge and delete all `CameraRowWidget` children from `camera_list_layout`.
     - Re-display placeholder label: `"No cameras discovered. Click 'Connect' to discover channels."`
     - Reset `RecordingsTableModel` to 0 rows.
     - Reset segment counter text to `"0 segments discovered (0 B) | 0 selected (0 B)"`.
     - Reset Stream Quality dropdown back to its default state (`HD (Main Stream)`).
     - Reset progress bar to `0%`, transfer status text to `"Idle"`, throughput to `"0.0 Mbps"`, and ETA label.
     - Revert footer status strictly to `"Disconnected · Ready"`.

5. **Live Console Header & Dedicated Progress Bar**:
   - Restructure Live Console section into a clean 3-tier hierarchy:
     - **Tier 1 (Header Line)**: Flat section title `[ LIVE CONSOLE ]` on left, `[ Clear ]` button on far right.
     - **Tier 2 (Dedicated Status & Progress Bar Line)**:
       - Sits directly beneath header line across full card width.
       - Left: Styled `QProgressBar` (height `10px`, radius `4px`).
       - Right: Status readout: `[ 0% ]  Idle  |  0.0 Mbps  |  Elapsed: 00:00  |  ETA: --:--`.
     - **Tier 3 (Terminal Console)**: Monospaced `QPlainTextEdit` terminal area below progress bar.

6. **Interactive Keychain Retrieval & Reactive Auto-Fill**:
   - Connect `editingFinished` on both `host_input` and `user_input` to auto-fill handler `_on_connection_field_changed`.
   - When fired: query `get_nvr_password(host, user, port)`.
   - If found:
     - Auto-fill `password_input`.
     - Check `remember_cb`.
     - Set visual tooltip cue `"🔑 Loaded from OS Keychain"`.
     - Log retrieval to console: `[INFO] Retrieved stored credentials from OS Keychain for <user>@<host>:<port>`.

---

## Addendum: Additional UI Refinements & Bug Fixes

7. **Left Panel Camera List Compact Spacing**:
   - Tighten vertical padding in `CameraRowWidget` (`setContentsMargins(6, 1, 6, 1)`, `spacing=4`).
   - Reduce spacing in `camera_list_layout` (`setSpacing(2)`, `setContentsMargins(0, 0, 0, 0)`).
   - In `style.py`, set `QWidget#cameraRow` padding to `1px 4px`.

8. **Left Panel Camera Numbers & Hardware Model Display**:
   - Add `model: str = ""` field to `Camera` Pydantic model in `core/models.py`.
   - Populate `model` from InputProxy discovery in `discover_cameras_isapi()`.
   - In `CameraRowWidget`:
     - Display channel number and name in checkbox: `f"CH{int(camera.number):02d}  {camera.name}"`.
     - Display hardware model on the right column as a compact badge `QLabel(camera.model)`.

9. **Right Panel Recording Files Summary Relocation**:
   - Move `summary_label` (`0 segments discovered ...`) from top bar to a dedicated bottom bar directly below `self.table_view`.
   - Keep top bar clean with Section Header (`RECORDINGS / VIDEO FILES`) and `Select All` / `Clear` buttons.

10. **Table File Row Numbers & Column Header Typography**:
    - Enable `self.table_view.verticalHeader().setVisible(True)`.
    - Ensure `RecordingsTableModel.headerData(orientation=Qt.Orientation.Vertical)` returns `str(section + 1)`.
    - Increase `QHeaderView::section` font size to `13px` with `font-weight: 700`.

11. **Eye-Friendly Light Mode Palette (Off-White & Soft Grey Shades)**:
    - In `style.py`, overhaul `LIGHT_THEME_QSS` to eliminate blinding pure white glare:
      - Window / Canvas background: `#ECEFF3` (soft slate grey).
      - Header & Footer frames: `#E2E8F0` with `#CBD5E1` borders.
      - Card frames: `#F8FAFC` with `#CBD5E1` borders.
      - Download Settings frame: `#F1F5F9` with `#CBD5E1` borders.
      - Inputs: `#FFFFFF` with `#CBD5E1` borders and `#1E293B` text.
      - Table alternate rows: `#FFFFFF` and `#F8FAFC`.
      - Table Header: `#E2E8F0` with `#475569` text.
      - Terminal console in light mode: Sleek dark slate `#1E293B` with crisp `#F1F5F9` text.

12. **Preserve Section Geometries**:
    - Strictly preserve all section heights, minimum heights, and window sizes (`camera_scroll.setMinimumHeight(455)`).

---

## Technical Details & Proposed Changes

### 1. `src/hikvision_downloader/core/models.py`
- Add `model: str = Field(default="", description="Camera hardware model")` to `Camera`.

### 2. `src/hikvision_downloader/core/cameras.py`
- In `discover_cameras_isapi()`, pass `model=ch_info.get("model", "")` when instantiating `Camera`.

### 3. `src/hikvision_downloader/ui/main_window.py`
- In `CameraRowWidget`:
  - Set tight margins: `setContentsMargins(6, 1, 6, 1)` and `setSpacing(4)`.
  - Format checkbox text as `f"CH{int(camera.number):02d}  {camera.name}"`.
  - Add model badge `QLabel(camera.model)` if `camera.model` is present.
- In `_build_recordings_view_panel()`:
  - Enable `self.table_view.verticalHeader().setVisible(True)`.
  - Move `summary_label` to bottom bar beneath `self.table_view`.

### 4. `src/hikvision_downloader/ui/models.py`
- In `RecordingsTableModel.headerData()`:
  - Add vertical header support returning `str(section + 1)`.

### 5. `src/hikvision_downloader/ui/style.py`
- Update `QWidget#cameraRow` padding to `1px 4px`.
- Update `QHeaderView::section` font-size to `13px; font-weight: 700;`.
- Update `LIGHT_THEME_QSS` with balanced slate/off-white grey palette (`#ECEFF3` canvas, `#E2E8F0` headers, `#F8FAFC` cards, `#1E293B` console).

---

## Verification Plan
1. Unit tests: `uv run pytest tests/unit/test_ui.py`.
2. Full test suite: `uv run pytest tests/unit tests/functional tests/integration/test_live_nvr.py`.
3. Strict type checking: `uv run mypy src tests`.
4. Linting & Formatting: `uv run ruff check .` & `uv run ruff format --check .`.
5. Update walkthrough in `.gemini/logs/task-007-zg-walkthrough.md`.
