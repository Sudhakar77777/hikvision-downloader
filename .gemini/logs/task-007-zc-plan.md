# Implementation Plan - Task 007-ZC: Critical UI Resizing, Scroll Areas, Font Cleanup & Layout Integrity

## 1. Task Analysis & Requirements
This task addresses initial launch sizing, splitter collapse, font warnings (`qt.qpa.fonts`), camera checklist vertical crushing, and widget clipping reported in `.gemini/tasks/007-zc-ui-bugs2.md`.

### Key Deliverables:
1. **Fix Font Alias Engine Warnings (`qt.qpa.fonts`)**:
   - In [`src/hikvision_downloader/ui/style.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/style.py):
     - Remove `-apple-system` and `BlinkMacSystemFont` across `DARK_THEME_QSS` and `LIGHT_THEME_QSS`.
     - Standardize typography font-family:
       `font-family: ".AppleSystemUIFont", "SF Pro Text", "Segoe UI", "Helvetica Neue", Arial, sans-serif;`
     - Terminal console font-family:
       `font-family: "SF Mono", "JetBrains Mono", Consolas, "Courier New", monospace;`
2. **Adaptive Window Startup Sizing & Centering**:
   - In [`src/hikvision_downloader/ui/main_window.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py):
     - Calculate launch size dynamically from `QApplication.primaryScreen().availableGeometry()`:
       `width = max(1240, min(1440, int(screen.width() * 0.85)))`
       `height = max(820, min(940, int(screen.height() * 0.85)))`
     - Fallback cleanly for headless/offscreen test environments.
     - Center window on screen: `self.move(screen.center() - self.rect().center())`.
     - Set hard minimum window size: `1180x760`.
3. **Prevent Left Panel Collapse & Enforce Hard Constraints**:
   - Store `self.left_panel` with `setMinimumWidth(380)`.
   - On `self.main_splitter`:
     - `setCollapsible(0, False)`
     - `setStretchFactor(0, 0)` (left panel locked to ideal width)
     - `setStretchFactor(1, 1)` (right operational panel expands dynamically)
     - Explicit initial sizes: `setSizes([390, width - 390])`.
4. **Isolate Camera Checklist in a Bounded Scroll Area**:
   - In `_build_camera_group()`:
     - Wrap `self.camera_list_container` in a dedicated `QScrollArea`:
       - `setWidgetResizable(True)`
       - `setMinimumHeight(140)`
       - `setMaximumHeight(220)`
       - `setFrameShape(QFrame.Shape.NoFrame)`
     - Prevents dynamic 11+ camera channel discovery from pushing date picker, presets, time inputs, and search button offscreen.
5. **Fix macOS Time Combo Box Clipping & Styling**:
   - In `_build_time_window_group()`:
     - Expand `start_hh_combo`, `start_mm_combo`, `end_hh_combo`, `end_mm_combo` to `65px` width.
   - In `style.py`:
     - Update `QComboBox` stylesheet rules with `padding: 2px 4px 2px 8px; min-height: 24px;` and dropdown width `18px`.
     - Ensure disabled text under `Full Day` is clearly readable (`#94A3B8` / `#64748B`).
6. **Left Panel Controls Spacing & Button Labels**:
   - "Refresh Channels" button: `setMinimumWidth(120)` to prevent truncation.
   - Output Directory "Browse..." button: `setFixedWidth(85)` to display full text.
7. **Strict Type Safety & Verification**:
   - 100% type annotations across all modified functions/methods.
   - Verify zero `qt.qpa.fonts` warnings on startup.
   - Run `uv run pytest tests/unit/test_ui.py`, `uv run mypy src tests`, `uv run ruff check .`.
   - Document results in `.gemini/logs/task-007-zc-walkthrough.md`.

---

## 2. Target Files & Proposed Actions

| File | Operation | Description |
|---|---|---|
| `.gemini/logs/task-007-zc-plan.md` | Create | This execution plan for Task 007-ZC. |
| `src/hikvision_downloader/ui/style.py` | Modify | Remove unsupported font aliases, update `QComboBox` padding/height/dropdown width, and refine disabled state contrast. |
| `src/hikvision_downloader/ui/main_window.py` | Modify | Implement adaptive window sizing/centering, splitter constraints and collapse protection, bounded scroll area for camera list, 65px time combos, and button min widths. |
| `tests/unit/test_ui.py` | Modify | Update unit tests to verify adaptive geometry bounds, splitter constraints, camera scroll area bounds, and 65px combo widths. |
| `.gemini/logs/task-007-zc-walkthrough.md` | Create (Phase 2) | Walkthrough document detailing all implemented changes and verification logs. |

---

## 3. Detailed Logic, Geometry & Styling Specifications

### 3.1 Font Family Definitions (`style.py`)
```css
/* Typography */
QWidget {
    font-family: ".AppleSystemUIFont", "SF Pro Text", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* Console Log */
QPlainTextEdit#consoleLog {
    font-family: "SF Mono", "JetBrains Mono", Consolas, "Courier New", monospace;
    font-size: 12px;
}

/* QComboBox */
QComboBox {
    padding: 2px 4px 2px 8px;
    min-height: 24px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
}
```

### 3.2 Adaptive Window Startup Sizing & Centering (`main_window.py`)
```python
screen_obj = QApplication.primaryScreen()
if screen_obj is not None:
    screen = screen_obj.availableGeometry()
    width = max(1240, min(1440, int(screen.width() * 0.85)))
    height = max(820, min(940, int(screen.height() * 0.85)))
    self.resize(width, height)
    self.move(screen.center() - self.rect().center())
else:
    self.resize(1320, 880)
self.setMinimumSize(1180, 760)
```

### 3.3 Main Splitter & Left Panel Constraints
```python
self.left_panel = QWidget(self)
self.left_panel.setMinimumWidth(380)

self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
self.main_splitter.setHandleWidth(6)
self.main_splitter.addWidget(self.left_panel)
self.main_splitter.addWidget(right_widget)
self.main_splitter.setCollapsible(0, False)
self.main_splitter.setStretchFactor(0, 0)
self.main_splitter.setStretchFactor(1, 1)
self.main_splitter.setSizes([390, self.width() - 390])
```

### 3.4 Camera List Bounded Scroll Area
```python
self.camera_scroll = QScrollArea(self)
self.camera_scroll.setWidgetResizable(True)
self.camera_scroll.setFrameShape(QFrame.Shape.NoFrame)
self.camera_scroll.setMinimumHeight(140)
self.camera_scroll.setMaximumHeight(220)
self.camera_scroll.setWidget(self.camera_list_container)
layout.addWidget(self.camera_scroll)
```

### 3.5 Time Combos & Button Widths
- `self.start_hh_combo.setFixedWidth(65)`
- `self.start_mm_combo.setFixedWidth(65)`
- `self.end_hh_combo.setFixedWidth(65)`
- `self.end_mm_combo.setFixedWidth(65)`
- `btn_refresh.setMinimumWidth(120)`
- `browse_btn.setFixedWidth(85)`

---

## 4. Verification & Testing Plan

1. **Unit Test Suite Execution**:
   - Run `uv run pytest tests/unit/test_ui.py`.
   - Verify tests assert:
     - `self.left_panel.minimumWidth() >= 380`
     - `self.main_splitter.isCollapsible(0) == False`
     - `self.camera_scroll.maximumHeight() == 220`
     - `self.start_hh_combo.width() == 65`
2. **Static Type Analysis**:
   - `uv run mypy src tests` (100% strict type safety, zero errors).
3. **Linting and Code Standards**:
   - `uv run ruff check .` (zero warnings).
4. **Font Warning Elimination**:
   - Verify launching the desktop app outputs zero `qt.qpa.fonts` warnings on stderr.
5. **Execution Summary**:
   - Document complete verification in `.gemini/logs/task-007-zc-walkthrough.md`.
