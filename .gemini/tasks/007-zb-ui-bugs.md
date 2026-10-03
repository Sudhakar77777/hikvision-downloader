CRITICAL UI POLISHING, LIGHT-MODE THEMING & ERGONOMIC REFACTOR

Refactor `src/hikvision_downloader/ui/` to resolve the contrast, alignment, styling, and branding bugs exposed in both Dark and Light modes. Adhere strictly to `.gemini/rules/4-coding-standards.md` with 100% type annotations across all functions and methods.

### 1. Fix Severe Console Text Contrast in Light Mode
- In `src/hikvision_downloader/ui/style.py`:
  - For `LIGHT_THEME_QSS`:
    - Option A: Style the `QPlainTextEdit` console with a crisp light theme (background `#F8FAFC`, border `#CBD5E1`, text `#0F172A`, timestamps `#64748B`, info `#0284C7`, success `#16A34A`, error `#DC2626`).
    - Option B: If keeping a dark developer console in both modes, lock its stylesheet strictly so text is NEVER dark: background `#0F172A`, text `#E2E8F0`, log prefixes `#38BDF8` / `#4ADE80` regardless of the parent window theme.
  - Eliminate unreadable black-on-black or dark-gray-on-navy text.

### 2. Branding Asset & Footer Cleanup
- Copy `favicon.svg` (the flame/lamp vector icon) from the project root to `src/hikvision_downloader/ui/assets/arivedha_logo.svg`.
- In `main_window.py`:
  - Footer bar MUST use `arivedha_logo.svg` rendered cleanly at 18x18.
  - Label text MUST be strictly: **"Powered by Arivedha"** (remove "Solutions").
  - Inspect top window/widget properties: eliminate any orphan label or title string that causes "Powered by Arivedha Solutions" to bleed as a ghost title at the top of the window frame.

### 3. Top Connection Bar Professional Layout
- Wrap top bar controls in a styled `QFrame` with unified horizontal alignment (`alignment=Qt.AlignmentFlag.AlignVCenter`):
  - Spacing: `spacing=10`, `margins=(12, 8, 12, 8)`.
  - Fix inputs:
    - Host: `minWidth=130px`
    - Port: `width=55px` (clean QSpinBox or QLineEdit without squishing neighboring fields)
    - User: `minWidth=100px`
    - Password: `minWidth=110px`
    - "Save in Keychain" checkbox: ensure baseline vertical alignment matches text fields.
    - Status pill: proper padding (`padding: 4px 10px; border-radius: 12px; font-weight: bold;`).
    - Theme button: clean icon/text toggle on the right.

### 4. Professional Restructuring of Investigation Time Window
- In `main_window.py`, clean up the time controls:
  - Presets Row: 4 uniform `QPushButton` elements in an even `QHBoxLayout` (`Morning`, `Afternoon`, `Evening`, `Full Day`) with standard button heights (`26px`) and legible text.
  - Custom Time Range Row: An aligned, balanced `QHBoxLayout`:
    `From:  [ HH ▼ ] : [ MM ▼ ]    To:  [ HH ▼ ] : [ MM ▼ ]`
    - `HH` combo width `52px`, `MM` combo width `52px`.
    - Colons `:` centered with `width=10px` and zero bloated margins.
    - Equal spacing between `From` group and `To` group.
    - Checkbox: `Full Day (00:00 - 23:59)` kept right above presets, checked by default.

### 5. Primary Action Button Styling ("START BATCH DOWNLOAD")
- Update styles in both Dark and Light QSS:
  - Enabled state: Solid Flame Orange (`#F37021`), bold crisp white text (`#FFFFFF`), `padding: 10px 20px`, `border-radius: 6px`.
  - Hover state: `#E05D0D`.
  - Disabled state: Slate background (`#94A3B8` light / `#334155` dark), subtle gray text (`#E2E8F0` / `#64748B`), clear disabled cursor.

### 6. Camera Checklist Visuals
- Add hover highlight and subtle alternating background or row padding to the camera list widget so rows feel distinct and easy to read.
- Ensure the radio toggle between `Global Stream (All Cameras)` and `Per-Camera Override` functions smoothly without leaving orphaned dropdowns.

### 7. Strict Type Annotations Enforcement
- Every function, method, signal handler, and callback in `src/hikvision_downloader/ui/` must have 100% explicit type annotations (parameters and return types). Zero bare `Any` and zero missing return types (`-> None`, `-> bool`, etc.).
- Run:
  1. `uv run ruff check .`
  2. `uv run mypy src tests`
  3. `uv run pytest tests/unit/test_ui.py`
- Document the verification and updated layout in `.gemini/logs/task-007-za-walkthrough.md`.