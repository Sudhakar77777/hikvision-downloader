# Implementation Plan - Task 007-ZD: Font Aliasing, Clean Typography, Control Symmetry & Ergonomics Refactor

## 1. Task Analysis & Requirements
This task addresses font alias warnings (`qt.qpa.fonts`), left panel layout stability, redundant time controls, browse button truncation, radio button geometry, table toolbar clutter, and top connection bar state symmetry reported in `.gemini/tasks/007-zd-ui-bugs3.md`.

### Key Deliverables:
1. **Fix Font Alias Warning on macOS (`qt.qpa.fonts`)**:
   - In [`src/hikvision_downloader/ui/style.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/style.py):
     - Remove `"SF Mono"` and `".AppleSystemUIFont"` entirely.
     - Set standard global typography font:
       `font-family: "Helvetica Neue", "Segoe UI", Arial, sans-serif;`
     - Set standard monospace console font:
       `font-family: Menlo, Monaco, Consolas, "Courier New", monospace;`
     - Verify zero font alias warnings on startup.
2. **Left Panel Width Enforcement & Layout Stability**:
   - In [`src/hikvision_downloader/ui/main_window.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py):
     - Enforce hard minimum width: `self.left_panel.setMinimumWidth(410)`.
     - In `showEvent(event)`: explicitly set splitter sizes and non-collapsible left panel:
       `self.main_splitter.setSizes([420, max(self.width() - 420, 750)])`
       `self.main_splitter.setCollapsible(0, False)`
3. **Investigation Time Window: Simplify & Remove Redundancy**:
   - Remove redundant `Full Day (00:00 - 23:59)` checkbox.
   - Group date picker, presets, and time range into 3 clean, balanced rows:
     - Row 1: `Date:` field with spacious `QDateEdit` (`calendarPopup=True`).
     - Row 2: 4 compact, uniform preset buttons: `AM (08-12)`, `NOON (12-18)`, `PM (18-24)`, `FULL (00-24)` (`setFixedHeight(26)`).
     - Row 3: Symmetrical time range layout:
       `From: [ HH ] : [ MM ]      To: [ HH ] : [ MM ]`
       - Colons `:` centered in `10px`.
       - Combo boxes width `56px` with compact padding.
   - Default range: `00:00` to `23:59`. Search queries use the selected time range directly.
4. **Replace Browse Text with Folder Icon**:
   - Replace `Browse...` text button with compact `QPushButton` / `QToolButton` using `📂` icon of fixed size `32x26px`.
   - Prevents text truncation (`3ro...`) and maximizes line edit path visibility.
5. **Fix Radio Button Shapes (True Circles)**:
   - In `style.py`, update `QRadioButton::indicator`:
     - Unchecked: `width: 14px; height: 14px; border-radius: 7px;`
     - Checked: `background-color: #F37021; border: 2px solid #FFFFFF; border-radius: 7px;`
6. **Remove Clutter from Table Action Header**:
   - Remove range selection spinner controls (`range_start_spin`, `range_count_spin`, `apply_range_btn`).
   - Retain clean header: `[Summary Label]`, stretch, `[Select All]`, `[Clear]`.
7. **Professional Top Connection Bar (Symmetry & State Toggle)**:
   - Header Title: Explicitly flat header with no input border.
   - Connect / Disconnect Toggle:
     - Disconnected: Button displays `"Connect"`.
     - Connected: Button displays `"Disconnect"`. Clicking disconnects session, resets discovered state, and returns to `"Connect"`.
   - Status Pill: `padding: 2px 8px; font-size: 11px; border-radius: 12px; font-weight: bold;` to match neighboring controls symmetrically.
   - Theme Toggle: Compact icon toggle (`🌙` / `☀️`) of fixed size `36x28px`.
8. **Strict Verification & Testing**:
   - Run `uv run pytest tests/unit/test_ui.py`.
   - Run `uv run mypy src tests` (100% type safety).
   - Run `uv run ruff check .`.
   - Document in `.gemini/logs/task-007-zd-walkthrough.md`.

---

## 2. Target Files & Proposed Actions

| File | Operation | Description |
|---|---|---|
| `.gemini/logs/task-007-zd-plan.md` | Create | This execution plan for Task 007-ZD. |
| `src/hikvision_downloader/ui/style.py` | Modify | Update font-families, circular radio button indicators, status pill padding/font-size, and compact combo box styles. |
| `src/hikvision_downloader/ui/main_window.py` | Modify | Implement Connect/Disconnect toggle, 36x28 theme icon button, 32x26 folder button, 410px left panel min width, `showEvent` splitter sizing, remove Full Day checkbox & range spins, implement AM/NOON/PM/FULL presets, and 56px time combos. |
| `tests/unit/test_ui.py` | Modify | Update unit tests to verify Connect/Disconnect toggle, folder button, removed range spins, 56px combo widths, and 410px panel min width. |
| `.gemini/logs/task-007-zd-walkthrough.md` | Create (Phase 2) | Walkthrough document detailing all implemented changes and verification logs. |

---

## 3. Detailed Logic, Geometry & Styling Specifications

### 3.1 Typography & Console Font Definitions (`style.py`)
```css
/* Typography */
QWidget {
    font-family: "Helvetica Neue", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

/* Console Log */
QPlainTextEdit#consoleLog {
    font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
    font-size: 12px;
}

/* Radio Button Indicator */
QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 1px solid #475569;
    background-color: #162032;
}

QRadioButton::indicator:hover {
    border-color: #38BDF8;
}

QRadioButton::indicator:checked {
    background-color: #F37021;
    border: 2px solid #FFFFFF;
    border-radius: 7px;
}

/* Status Pill */
QLabel#statusBadge {
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 11px;
}
```

### 3.2 Main Splitter & Left Panel Sizing (`main_window.py`)
```python
self.left_panel.setMinimumWidth(410)


def showEvent(self, event: QShowEvent) -> None:
    super().showEvent(event)
    if hasattr(self, "main_splitter"):
        self.main_splitter.setSizes([420, max(self.width() - 420, 750)])
        self.main_splitter.setCollapsible(0, False)
```

### 3.3 Connect / Disconnect Toggle Logic
```python
def _on_connect_clicked(self) -> None:
    if self._session is not None:
        self._disconnect_session()
        return

    # Normal connect worker launch...


def _disconnect_session(self) -> None:
    if self._download_worker is not None and self._download_worker.isRunning():
        self._download_worker.cancel()
    if self._search_worker is not None and self._search_worker.isRunning():
        self._search_worker.cancel()
    self._session = None
    self._discovered_cameras.clear()
    self._camera_rows.clear()
    self._discovered_dates.clear()
    self._rebuild_camera_checklist()
    self._table_model.clear()
    self.status_badge.setText("● Disconnected")
    self.status_badge.setStyleSheet(
        "background-color: #334155; color: #94A3B8; border-radius: 12px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
    )
    self.connect_btn.setText("Connect")
    self.log_message("INFO", "Disconnected from NVR session.")
```

### 3.4 Compact Theme & Folder Buttons
- Theme Button: `self.theme_btn = QPushButton("☀️" if self._is_dark_theme else "🌙", self)`, `setFixedSize(36, 28)`.
- Browse Button: `browse_btn = QPushButton("📂", self)`, `setFixedSize(32, 26)`.

---

## 4. Verification & Testing Plan

1. **Unit Test Suite Execution**:
   - Run `uv run pytest tests/unit/test_ui.py`.
   - Verify tests assert:
     - `self.left_panel.minimumWidth() >= 410`
     - `self.start_hh_combo.width() == 56`
     - Connect / Disconnect button toggle transitions.
     - Select All / Clear table toolbar actions.
2. **Static Type Analysis**:
   - `uv run mypy src tests` (100% strict type safety, zero errors).
3. **Linting and Code Standards**:
   - `uv run ruff check .` (zero warnings).
4. **Execution Summary**:
   - Document complete verification in `.gemini/logs/task-007-zd-walkthrough.md`.
