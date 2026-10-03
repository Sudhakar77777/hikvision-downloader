CRITICAL UI RESIZING, SCROLL AREAS, FONT CLEANUP & LAYOUT INTEGRITY

Address the initial launch sizing, splitter collapse, font warnings, and widget clipping in `src/hikvision_downloader/ui/`. Follow `.gemini/rules/4-coding-standards.md` strictly.

### 1. Fix the Font Alias Engine Warning (`qt.qpa.fonts`)
- In `src/hikvision_downloader/ui/style.py`:
  - Search and remove all occurrences of `-apple-system` and `BlinkMacSystemFont` across `DARK_THEME_QSS` and `LIGHT_THEME_QSS`.
  - Replace them with clean Qt-supported font definitions:
    `font-family: ".AppleSystemUIFont", "SF Pro Text", "Segoe UI", "Helvetica Neue", Arial, sans-serif;`
  - For the console terminal, use:
    `font-family: "SF Mono", "JetBrains Mono", Consolas, "Courier New", monospace;`

### 2. Adaptive Window Startup Sizing & Proportions
- In `main_window.py`:
  - Calculate initial window size dynamically based on available screen geometry:
    ```python
    screen = QApplication.primaryScreen().availableGeometry()
    width = max(1240, min(1440, int(screen.width() * 0.85)))
    height = max(820, min(940, int(screen.height() * 0.85)))
    self.resize(width, height)
    self.setMinimumSize(1180, 760)
    ```
  - Center the window on the screen on first launch:
    `self.move(screen.center() - self.rect().center())`

### 3. Prevent Left Panel Collapse & Enforce Hard Constraints
- In `main_window.py`:
  - Set a hard minimum width on the left container widget:
    `self.left_panel.setMinimumWidth(380)`
  - On the main `QSplitter`:
    `self.main_splitter.setCollapsible(0, False)`
    `self.main_splitter.setStretchFactor(0, 0)` # Left panel stays fixed to its ideal width
    `self.main_splitter.setStretchFactor(1, 1)` # Right panel expands with window resizing
  - Set explicit initial splitter sizes:
    `self.main_splitter.setSizes([390, width - 390])`

### 4. Isolate the Camera Checklist inside a Bounded Scroll Area
- To prevent dynamic camera loading (11+ channels) from vertically crushing the time window and download controls:
  - Place the camera rows container inside a `QScrollArea`:
    - `scroll_area.setWidgetResizable(True)`
    - `scroll_area.setMaximumHeight(220)` # Bounded height so controls below never shift
    - `scroll_area.setMinimumHeight(140)`
    - Clean styled scrollbars via QSS.

### 5. Fix macOS Time Combo Box Clipping
- In `_build_time_window_group()`:
  - Increase combo box widths to at least `65px` (`setFixedWidth(65)` or `setMinimumWidth(65)`).
  - In `style.py`, add custom styling for `QComboBox`:
    ```css
    QComboBox {
        padding: 2px 4px 2px 8px;
        min-height: 24px;
    }
    QComboBox::drop-down {
        width: 18px;
    }
    ```
  - Ensure the digits (`00`, `08`, `12`, etc.) are clearly visible and never clipped behind the dropdown arrow.
  - When disabled (under `Full Day`), ensure text remains legible (`#94A3B8` / `#64748B`) rather than invisible or faded out.

### 6. Left Panel Controls Spacing & Button Labels
- Ensure "Refresh Channels" has enough room (`minWidth=120px`) and never truncates to "Refresh Cl".
- Ensure the Output Directory "Browse..." button has fixed width `85px` and displays the full label "Browse...".

### 7. Verification & Static Analysis
- Verify that launching the app produces ZERO `qt.qpa.fonts` warnings on stdout/stderr.
- Verify that when the app launches, all buttons ("Refresh Channels", "Browse...", "Save in Keychain") are fully legible without manual window stretching.
- Run `uv run pytest tests/unit/test_ui.py`.
- Run `uv run mypy src tests` to confirm 100% strict type safety.
- Run `uv run ruff check .`.
- Present the updated walkthrough in `.gemini/logs/task-007-zc-walkthrough.md`.