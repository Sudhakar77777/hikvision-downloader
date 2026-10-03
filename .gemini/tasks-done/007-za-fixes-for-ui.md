Execute UI polishing and ergonomic fixes for Task 007 according to `.gemini/rules/1-workflow.md` and `.gemini/rules/4-coding-standards.md`.

### 1. Window Sizing & Layout Geometry
- Set default window dimensions to at least 1280x860 with minimum size 1150x750.
- Adjust stretch factors across QSplitter and QLayout instances so controls never truncate:
  - Top connection bar: Provide sufficient minimum widths and padding for Host, Port, User, and Password fields; fix the right-hand status pill and "Save in Keychain" toggle so they are not compressed against the window margin.
  - Left panel: Ensure the "Refresh Channels" button displays its full label (not "Ref"), and the output directory Browse button displays full text "Browse...".
  - Right panel: Give "Select Range", "Select All", and "Clear" comfortable spacing above the table without crowding segment count text.

### 2. Branding & Logo Restructuring
- Top Header: Display the application title as "HikVision Downloader" alongside a clean, crisp application icon.
- Dedicated Footer/Branding Frame: Move Arivedha corporate branding to a dedicated footer bar at the bottom:
  - Embed the vector lamp/flame mark from `src/hikvision_downloader/ui/assets/favicon.svg` (or `logo.svg`).
  - Display "Powered by Arivedha" / "Arivedha Solutions".

### 3. Default Output Directory Resolution
- Update the default output directory initialization:
  - 1st Priority: `os.getenv("HIKVISION_OUTPUT_DIR")` if defined.
  - 2nd Priority (Default Fallback): `Path.home() / "Downloads" / "HikvisionArchive"`.
- Do not default to a repository-relative workspace directory. Ensure the path line edit displays the full path with tooltip and allows smooth expansion.

### 4. Simplified Stream Selection Toggle
- Refactor the stream selection UI to eliminate conflicting global vs. per-camera controls:
  - Add a radio toggle:
    - `(●) Global Stream (All Cameras)` [Default]
    - `( ) Per-Camera Override`
  - In `Global Stream` mode:
    - Display only the top global dropdown (HD / SD).
    - Hide individual stream dropdowns next to camera rows, keeping the camera checklist wide, clean, and unambiguous.
  - In `Per-Camera Override` mode:
    - Reveal per-camera stream dropdowns next to each camera row (defaulting to the camera's main stream).
    - If a camera only exposes a single track over ISAPI, display a static text badge for that stream instead of a dropdown.

### 5. Calendar Legibility, Recorded Dates & Theme Switching
- Theme Toggle: Add a clean Dark / Light Mode toggle switch in the top toolbar.
- Navigation Buttons: Style `QCalendarWidget` navigation buttons (`<` and `>`) with explicit contrast in QSS so arrow icons and month/year text are clearly visible in both dark and light modes.
- Recorded Dates Highlighting: Use `QTextCharFormat` to dynamically highlight calendar dates returned by `discover_available_dates()` with an accent dot/badge/background, enabling operators to see which days have recorded footage.

### 6. Time Range Selection Ergonomics
- Replace the cramped raw micro-spinners (`00:00:00`) with clean `HH:MM` combo boxes / dropdowns (`From: [HH] : [MM]` to `To: [HH] : [MM]`).
- Retain the "Full Day (00:00 - 23:59)" checkbox (checked by default), which disables custom time inputs until unchecked.
- Provide quick preset buttons or actions: "Morning (08:00 - 12:00)", "Afternoon (12:00 - 18:00)", "Evening (18:00 - 23:59)".

### Invariants & Verification
- Ensure `src/hikvision_downloader/core/` remains strictly free of PySide6 imports.
- Maintain 100% strict type annotations across all modified UI modules.
- Ensure headless unit tests pass with `QT_QPA_PLATFORM=offscreen`.
- Run `uv run ruff check .` and `uv run mypy src tests` to confirm zero static errors.
- Document changes in `.gemini/logs/task-007-walkthrough.md`.