# CRITICAL UI REFACTOR: FONT ALIASING, CLEAN TYPOGRAPHY, CONTROL SYMMETRY & ERGONOMICS

Execute a comprehensive visual cleanup of `src/hikvision_downloader/ui/` to eliminate all clipping, font warnings, redundant controls, and asymmetrical layouts shown in recent runs. Follow `.gemini/rules/4-coding-standards.md` strictly (100% explicit type annotations).

### 1. Fix Font Alias Warning on macOS (`qt.qpa.fonts`)
- In `src/hikvision_downloader/ui/style.py`:
  - Completely remove `"SF Mono"` and `".AppleSystemUIFont"` from all stylesheets.
  - Set global application font to:
    `font-family: -apple-system, system-ui, "SF Pro Text", "Helvetica Neue", Arial;` -> NO pseudo names. Use strictly:
    `font-family: "Helvetica Neue", "Segoe UI", Arial, sans-serif;`
  - For the terminal console (`#consoleLog`), use standard macOS-registered monospace fonts:
    `font-family: Menlo, Monaco, Consolas, "Courier New", monospace;`
  - Confirm application launch produces ZERO `qt.qpa.fonts` warnings on stderr.

### 2. Left Panel Width Enforcement & Layout Stability
- In `main_window.py`:
  - Enforce a hard minimum width on the left panel:
    `self.left_panel.setMinimumWidth(410)`
  - In `showEvent(event)`:
    Ensure splitter sizes are explicitly set so the left column never renders squeezed on initial window display:
    `self.main_splitter.setSizes([420, self.width() - 420])`
    `self.main_splitter.setCollapsible(0, False)`

### 3. Investigation Time Window: Simplify & Remove Redundancy
- Remove the redundant `Full Day (00:00 - 23:59)` checkbox completely.
- Group the date picker and quick presets compactly:
  - Row 1: `Date:` field with a spacious, easily clickable calendar popup button (`calendarPopup=True`).
  - Row 2: 4 compact, uniform preset buttons: `AM (08-12)`, `NOON (12-18)`, `PM (18-24)`, `FULL (00-24)`.
  - Row 3: Symmetrical time range layout with equal margins:
    `From: [ HH ] : [ MM ]      To: [ HH ] : [ MM ]`
    - Colons `:` centered in `10px` without margin bloat.
    - Combo boxes width `56px` with compact padding.

### 4. Replace Browse Text with Folder Icon
- In the Output Directory group:
  - Replace the text `Browse...` button with a `QToolButton` using a standard folder icon (`📂` or SVG asset) with fixed size `32x26px`.
  - This prevents text truncation (`3ro...`) and gives maximum width to the path display.

### 5. Fix Radio Button Shapes (Circular, Not Square)
- In `style.py`, fix `QRadioButton::indicator`:
  QRadioButton::indicator {
      width: 14px;
      height: 14px;
      border-radius: 7px;
  }
  QRadioButton::indicator:checked {
      background-color: #F37021;
      border: 2px solid #FFFFFF;
      border-radius: 7px;
  }

Ensure Global Stream and Per-Camera Override radio buttons render as true circles.

### 6. Remove Clutter from Table Action Header

* In the Right Panel table toolbar:
* Remove `Range: [ 1 ] Count: [ 10 ] [ Select Range ]` completely.
* Keep only: `[Segments count / size summary]`, `[Select All]`, and `[Clear]`.
* This eliminates visual noise and allows the status summary to breathe.



### 7. Professional Top Connection Bar (Symmetry & State Toggle)

* Title: Ensure `"HikVision Downloader"` is rendered as a clean, flat header (`QLabel` with bold typography), NOT styled with an input border/box.
* Connect / Disconnect Toggle:
* When disconnected: Button reads `"Connect"`.
* When connected: Button toggles to `"Disconnect"`, allowing the operator to disconnect and log in with different credentials.


* Status Pill: Adjust font size and padding (`padding: 2px 8px; font-size: 11px;`) to match neighboring controls symmetrically.
* Theme Toggle: Replace the bulky text button with a compact icon toggle (e.g. `🌙` / `☀️`) of fixed size `36x28px`.

### 8. Strict Verification

* Run `uv run pytest tests/unit/test_ui.py`.
* Run `uv run mypy src tests` (100% strict type checking).
* Run `uv run ruff check .`.
* Present the updated walkthrough in `.gemini/logs/task-007-zd-walkthrough.md`.
