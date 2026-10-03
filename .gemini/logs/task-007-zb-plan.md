# Implementation Plan - Task 007-ZB: PySide6 Desktop UI Polishing, Light-Mode Theming & Ergonomic Refactor

## 1. Task Analysis & Requirements
This task addresses specific visual, ergonomic, branding, and theming issues reported in `.gemini/tasks/007-zb-ui-bugs.md` across both Dark and Light modes.

### Key Deliverables:
1. **Console Text Contrast in Light Mode ([`src/hikvision_downloader/ui/style.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/style.py) & [`src/hikvision_downloader/ui/main_window.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py))**:
   - Resolve severe contrast issues where log messages rendered with invisible or dark text in light mode.
   - Implement **Option B (Standard Developer Console)**: Lock `QPlainTextEdit#consoleLog` to a crisp, dark developer terminal across both Light and Dark themes (`background: #0F172A`, `border: 1px solid #CBD5E1` in light / `#1E293B` in dark, `border-radius: 6px`, `padding: 8px`).
   - In `log_message()`, explicitly format message text with crisp foreground `#E2E8F0` and timestamps with `#94A3B8` instead of relying on default or `color: inherit`, eliminating dark-on-dark text completely.
2. **Branding Asset & Footer Cleanup**:
   - Copy root `favicon.svg` (the Arivedha flame/lamp vector icon) to [`src/hikvision_downloader/ui/assets/arivedha_logo.svg`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/assets/arivedha_logo.svg).
   - In `main_window.py`, update footer branding to render `arivedha_logo.svg` cleanly at `18x18` pixels.
   - Set footer label text strictly to: **"Powered by Arivedha"** (remove "Solutions").
   - Ensure clean window and widget titles (`"HikVision Downloader"`) with zero ghost title bleeding.
3. **Top Connection Bar Professional Layout**:
   - Wrap top bar controls in `QFrame#headerFrame` with unified vertical alignment (`Qt.AlignmentFlag.AlignVCenter`), `spacing=10`, and margins `(12, 8, 12, 8)`.
   - Constrain input field geometries:
     - Host: `minWidth=130px`
     - Port: Fixed `55px` width (centered text, compact without overflowing or squishing neighboring fields)
     - Username: `minWidth=100px`
     - Password: `minWidth=110px`
     - "Save in Keychain" checkbox: Clean vertical baseline alignment matching adjacent inputs.
     - Status pill: Unified styling (`padding: 4px 10px; border-radius: 12px; font-weight: bold;`).
     - Theme toggle button: Clean text/icon toggle aligned on the right.
4. **Professional Restructuring of Investigation Time Window**:
   - Reorganize time controls in `_build_time_window_group()`:
     - Keep `"Full Day (00:00 - 23:59)"` checkbox right above presets (checked by default).
     - Presets Row: 4 uniform `QPushButton` elements in an even `QHBoxLayout` (`Morning`, `Afternoon`, `Evening`, `Full Day`) with standard button heights (`26px`) and legible labels.
     - Custom Time Range Row: Balanced `QHBoxLayout`:
       `From:  [ HH ▼ ] : [ MM ▼ ]    To:  [ HH ▼ ] : [ MM ▼ ]`
       - `HH` combo width `52px`, `MM` combo width `52px` (editable for custom minutes).
       - Colons `:` centered with `width=10px` and zero bloated margins.
       - Clean spacing between From and To groups.
5. **Primary Action Button Styling ("START BATCH DOWNLOAD")**:
   - Update `QPushButton#primaryActionBtn` in both `DARK_THEME_QSS` and `LIGHT_THEME_QSS`:
     - Enabled state: Solid Flame Orange (`#F37021`), crisp white text (`#FFFFFF`), `padding: 10px 20px`, `border-radius: 6px`, `font-weight: 700`.
     - Hover state: `#E05D0D`.
     - Disabled state: Slate background (`#94A3B8` light / `#334155` dark), subtle legible text (`#E2E8F0` light / `#64748B` dark), and disabled cursor styling.
6. **Camera Checklist Visuals & Smooth Stream Mode Switching**:
   - Add hover highlight (`#1E293B` dark / `#F1F5F9` light), subtle rounded border, and comfortable padding to `CameraRowWidget` rows.
   - Verify smooth toggling between `Global Stream` and `Per-Camera Override` without orphaned dropdowns or lingering controls.
7. **Strict Type Annotations Enforcement & Verification**:
   - Ensure 100% type annotations across all functions, methods, slots, and callbacks in `src/hikvision_downloader/ui/` (zero bare `Any`, zero missing return types).
   - Execute test and lint suites: `uv run pytest tests/unit/test_ui.py`, `uv run mypy src tests`, `uv run ruff check .`.
   - Document verification in `.gemini/logs/task-007-zb-walkthrough.md`.

---

## 2. Target Files & Proposed Actions

| File | Operation | Description |
|---|---|---|
| `.gemini/logs/task-007-zb-plan.md` | Create | This execution plan for Task 007-ZB. |
| `src/hikvision_downloader/ui/assets/arivedha_logo.svg` | Create / Copy | Copy `favicon.svg` from project root to assets directory for Arivedha branding. |
| `src/hikvision_downloader/ui/style.py` | Modify | Update `DARK_THEME_QSS` and `LIGHT_THEME_QSS`: dark developer console styling, primary action button disabled states, camera row hover, preset buttons (`26px`), and status pill padding. |
| `src/hikvision_downloader/ui/main_window.py` | Modify | Top bar layout alignments and field widths, time presets row (`26px`) and `52px` combo boxes with `10px` colons, footer logo `arivedha_logo.svg` (`18x18`) with `"Powered by Arivedha"`, explicit `#E2E8F0` console HTML formatting, and camera row styling. |
| `tests/unit/test_ui.py` | Modify | Update and expand unit tests for time presets, branding asset resolution, and stream toggling. |
| `.gemini/logs/task-007-zb-walkthrough.md` | Create (Phase 2) | Walkthrough document detailing all implemented changes and verification logs. |

---

## 3. Detailed Logic, Geometry & Styling Specifications

### 3.1 Console Contrast in Light & Dark Mode
- In `src/hikvision_downloader/ui/style.py`:
  - `QPlainTextEdit#consoleLog` is styled as a dedicated developer terminal in both themes:
    - Background: `#0B0F19` (Dark) / `#0F172A` (Light)
    - Foreground: `#E2E8F0`
    - Border: `1px solid #1E293B` (Dark) / `1px solid #CBD5E1` (Light)
    - Border Radius: `6px`
    - Padding: `8px`
    - Font Family: JetBrains Mono / SF Mono / Consolas / monospace
- In `src/hikvision_downloader/ui/main_window.py` `log_message()`:
  - Timestamps: `<span style='color: #94A3B8;'>[{timestamp}]</span>`
  - Level badges: `<span style='color: {color}; font-weight: bold;'>[{level}]</span>`
  - Message body: `<span style='color: #E2E8F0;'>{message}</span>`
  - Colors: INFO (`#38BDF8`), SUCCESS (`#4ADE80`), WARN (`#F59E0B`), ERROR (`#EF4444`), SKIP (`#EAB308`), DOWNLOAD (`#F37021`).

### 3.2 Branding Asset & Footer Cleanup
- Copy `favicon.svg` from workspace root to `src/hikvision_downloader/ui/assets/arivedha_logo.svg`.
- In `src/hikvision_downloader/ui/main_window.py`:
  - `ARIVEDHA_LOGO_SVG_PATH = ASSETS_DIR / "arivedha_logo.svg"`
  - Footer logo rendered at `18x18` pixels with smooth aspect ratio scaling:
    `pix = QPixmap(str(ARIVEDHA_LOGO_SVG_PATH)).scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)`
  - Footer label: `QLabel("Powered by <b>Arivedha</b>", self)`
  - Window Title: `"HikVision Downloader"`

### 3.3 Top Connection Bar Layout
- `headerFrame` layout:
  - Margins: `(12, 8, 12, 8)`
  - Spacing: `10`
  - Alignment: `Qt.AlignmentFlag.AlignVCenter`
- Geometry constraints:
  - `self.host_input.setMinimumWidth(130)`
  - `self.port_input.setFixedWidth(55)`, `self.port_input.setAlignment(Qt.AlignmentFlag.AlignCenter)`, `self.port_input.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)`
  - `self.user_input.setMinimumWidth(100)`
  - `self.password_input.setMinimumWidth(110)`
  - `self.remember_cb`: aligned horizontally in the same `QHBoxLayout`
  - `self.status_badge`: `QLabel` with `padding: 4px 10px; border-radius: 12px; font-weight: bold;` across all status updates (Disconnected, Connecting, Connected, Auth Failed).
  - `self.theme_btn`: Clean button on the far right.

### 3.4 Investigation Time Window Restructuring
- Preset buttons:
  - 4 buttons: `Morning (08-12)`, `Afternoon (12-18)`, `Evening (18-24)`, `Full Day (00-24)` (or `Morning`, `Afternoon`, `Evening`, `Full Day`).
  - Height: `setFixedHeight(26)`.
- Time range layout:
  - `From:` `QLabel`
  - `start_hh_combo`: `setFixedWidth(52)`
  - Colon: `QLabel(":")`, `setFixedWidth(10)`, `setAlignment(Qt.AlignmentFlag.AlignCenter)`
  - `start_mm_combo`: `setFixedWidth(52)`, editable with 5-minute increments + custom entries.
  - Spacing: `addSpacing(12)`
  - `To:` `QLabel`
  - `end_hh_combo`: `setFixedWidth(52)`
  - Colon: `QLabel(":")`, `setFixedWidth(10)`, `setAlignment(Qt.AlignmentFlag.AlignCenter)`
  - `end_mm_combo`: `setFixedWidth(52)`, editable with 5-minute increments + "59".

### 3.5 Primary Action Button ("START BATCH DOWNLOAD")
- QSS rules for `QPushButton#primaryActionBtn`:
  - Dark Mode:
    - Default: `background-color: #F37021; color: #FFFFFF; font-size: 14px; font-weight: 700; padding: 10px 20px; border-radius: 6px;`
    - Hover: `background-color: #E05D0D;`
    - Pressed: `background-color: #C24E05;`
    - Disabled: `background-color: #334155; color: #64748B; border: 1px solid #1E293B;`
  - Light Mode:
    - Default: `background-color: #F37021; color: #FFFFFF; font-size: 14px; font-weight: 700; padding: 10px 20px; border-radius: 6px;`
    - Hover: `background-color: #E05D0D;`
    - Pressed: `background-color: #C24E05;`
    - Disabled: `background-color: #94A3B8; color: #E2E8F0; border: 1px solid #CBD5E1;`

### 3.6 Camera Checklist Visuals & Stream Mode
- `CameraRowWidget`:
  - `setObjectName("cameraRow")`
  - Margins: `(8, 4, 8, 4)`
  - QSS:
    - Dark: `background-color: #162032; border: 1px solid #1E293B; border-radius: 4px;` | Hover: `background-color: #1E293B; border-color: #38BDF8;`
    - Light: `background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 4px;` | Hover: `background-color: #F1F5F9; border-color: #1E6B7B;`
  - Stream mode radio switching toggles `set_override_mode(is_override)` cleanly across all camera rows.

---

## 4. Verification & Testing Plan

1. **Unit Test Suite Execution**:
   - `uv run pytest tests/unit/test_ui.py` (verify all 15+ headless Qt tests pass).
   - Verify specific assertions on `ARIVEDHA_LOGO_SVG_PATH`, time preset button heights, input constraints, and stream toggles.
2. **Static Type Analysis**:
   - `uv run mypy src tests` (strict check, zero errors).
3. **Linting and Code Standards**:
   - `uv run ruff check .` (enforce style and zero warnings).
4. **Execution Summary**:
   - Document full execution and verification results in `.gemini/logs/task-007-zb-walkthrough.md`.
