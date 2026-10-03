CRITICAL UI REFACTOR: RESOLVE QPA FONT ENGINE WARNING, STRIP LABEL BORDERS, MOVE DOWNLOAD SETTINGS & FIX SEARCH

Follow `.gemini/rules/4-coding-standards.md` strictly (100% explicit type annotations).

### 1. Root-Cause Fix for Font Warning (`qt.qpa.fonts: Missing font family "Segoe UI"`)
- Stop using web-style comma-separated fallback lists in QSS. Qt is scanning the OS for "Segoe UI" on macOS and stalling.
- In `src/hikvision_downloader/ui/style.py`:
  - REMOVE all `font-family` declarations from `DARK_THEME_QSS` and `LIGHT_THEME_QSS`.
- In `src/hikvision_downloader/ui/main_window.py` (inside `main()` or `__init__`):
  - Set the application-wide fonts programmatically using Qt's native system font resolution:
    ```python
    from PySide6.QtGui import QFontDatabase

    app = QApplication.instance() or QApplication(sys.argv)
    # UI General Font:
    general_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    app.setFont(general_font)
    ```
  - For `QPlainTextEdit#consoleLog`, apply the fixed monospace font programmatically:
    ```python
    fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    self.console_log.setFont(fixed_font)
    ```
- Confirm application launch outputs ZERO font warnings to stderr.

### 2. Strip Input Box Borders from All Text Labels
- In `src/hikvision_downloader/ui/style.py`:
  - Set global default:
    `QLabel { background: transparent; border: none; padding: 0px; }`
  - Ensure labels (`Host:`, `Port:`, `User:`, `Password:`, `From:`, `To:`, `HikVision Downloader`) render as flat text, not text boxes.
  - ONLY explicitly bordered badges (e.g., `QLabel#statusBadge`, disk space pills) may carry borders or background fills.

### 3. Top Connection Bar Layout, Spacing & Color Symmetry
- Tighten and align controls in `QHBoxLayout`:
  - `Host:` label + `QLineEdit` (max width `120px`), `Port:` label + `QSpinBox` (fixed width `50px`, no buttons, centered).
  - `User:` label + `QLineEdit` (max width `90px`), `Password:` label + `QLineEdit` (max width `90px`).
  - `Save in Keychain` checkbox (clean vertical baseline).
  - `12px` spacing, followed by the **Connect / Disconnect Button**:
    - Disconnected: Teal/Emerald (`#1E6B7B`), bold white text, labeled `"Connect"`.
    - Connected: Crimson/Red (`#DC2626`), bold white text, labeled `"Disconnect"`.
  - Status Pill: Compact pill (`padding: 2px 6px; font-size: 10px; border-radius: 8px;`).
  - Theme Toggle: Compact icon button (`32x26px`, `padding: 0px`, centered `☀️` / `🌙`, no clipped borders).

### 4. Simplify Stream Selection (Remove Per-Camera Override)
- In `_build_camera_group()`:
  - Remove `Global Stream` vs `Per-Camera Override` radio buttons entirely.
  - Camera list displays clean rows with checkboxes and camera names in the scroll area.
  - Beneath the camera list, provide a single clean **Stream Quality** dropdown:
    - Inspect discovered cameras: if only Main Stream exists, display ONLY `HD (Main Stream)`.
    - Do not offer non-existent stream tracks.

### 5. Investigation Time Window Cleanup
- No spaces around colons: `From: [HH]:[MM]  To: [HH]:[MM]`.
- Remove redundant `Full Day` checkboxes if preset buttons exist.

### 6. Workflow Panel Reorganization
- **LEFT PANEL (Sources & Selection Only)**:
  - 1. Camera Channels & Stream Quality dropdown.
  - 2. Investigation Time Window (Date picker, Presets `AM / NOON / PM / FULL`, `From: HH:MM  To: HH:MM`).
  - 3. **`[ 🔍 SEARCH RECORDINGS ]`** button pinned at the bottom of the left panel.
  - **REMOVE `Download Settings` from the left panel entirely.**

- **RIGHT PANEL (Table, Download Controls, Actions & Logs)**:
  - Top: Segments Table (`[Summary]`, `[Select All]`, `[Clear]`).
  - Middle: **Download Settings Frame** (2 compact lines directly beneath the table):
    - Line 1: `Output Directory: [ path... ] [📂] [ Disk Space Pill ]`
    - Line 2: `Concurrent Workers: [1 2 3 4]  [✓] Generate recording-list.csv manifest`
  - Primary Action: `[ ⬇ START BATCH DOWNLOAD ]` (`#F37021`) + `[ ✕ CANCEL / ABORT ]`.
  - Bottom: **Live Activity Console**:
    - Integrate the progress status (`Idle`, `0%`, `Mbps`, `ETA`) into the header bar of the console to conserve vertical space.
    - Monospaced console text box below it.

### 7. Fix Search Execution
- Resolve the issue preventing `[ 🔍 SEARCH RECORDINGS ]` from populating segments.
- Ensure `SearchWorker` receives active session credentials, queries `CMSearch` across selected camera track IDs, populates `RecordingsTableModel`, and emits logs cleanly to the console.

### 8. Verification & Delivery
- Confirm application launch outputs ZERO `qt.qpa.fonts` warnings on stderr.
- Run `uv run pytest tests/unit/test_ui.py`.
- Run `uv run mypy src tests` (100% strict type safety).
- Run `uv run ruff check .`.
- Present the updated walkthrough in `.gemini/logs/task-007-ze-walkthrough.md`.