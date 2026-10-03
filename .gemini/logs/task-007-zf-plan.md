# Task 007-ZF Implementation Plan: UI Polish Pass & Hardware Status

## Objectives
Execute the specific UI polish items specified in `.gemini/tasks/007-zf-ui-bugs.md`:
1. **Top Connection Bar**:
   - Increase `user_input` minimum width to `115px`.
   - Clear focus on host/user/password inputs upon successful authentication and set focus to `search_btn`.
   - Set matching `28px` height for `status_badge` (`height: 28px; line-height: 28px; padding: 2px 10px; font-size: 11px;`) and `theme_btn` (`32x28px`).
2. **Left Panel**:
   - Set `camera_scroll` minimum height to `240px` and remove restrictive maximum height clamping.
   - Verify `Deselect` button iterates through all rows and sets `row.checkbox.setChecked(False)`.
   - Format camera names to show hardware model if available (`D1 MainGate (DS-2CD2143G0-I)` or `D1 MainGate`).
   - Rename group box title from `INVESTIGATION TIME WINDOW` to `RECORDING TIME WINDOW`.
   - In `style.py`, enlarge `QDateEdit::drop-down` target width to `32px`.
3. **Right Panel**:
   - Add clean section header `RECORDINGS / VIDEO FILES` above the recordings table.
   - Add clean section header `DOWNLOAD SETTINGS` in the download settings card.
   - Rename `Live Activity Console` to `Live Console`.
   - Symmetrically align console header in a single centered `QHBoxLayout`:
     `[Live Console]  [Progress Bar: 0%]  [Idle | 0.0 Mbps | Elapsed: 00:00]  [Clear (24px)]`.
4. **Dynamic NVR Hardware Status in Footer**:
   - Replace static version text with dynamic label `self.footer_device_label`.
   - When disconnected: `"Disconnected · Ready"`.
   - When connected: Query `/ISAPI/System/deviceInfo` and display `Model: <model>  |  Firmware: <firmware>  |  Active Channels: <count>`, falling back to `Connected: <host> (<count> Channels)`.
5. **Verification**:
   - Run `uv run pytest tests/unit/test_ui.py`.
   - Run `uv run pytest tests/unit tests/functional`.
   - Run `uv run mypy src tests`.
   - Run `uv run ruff check .` and `uv run ruff format --check .`.
   - Write walkthrough in `.gemini/logs/task-007-zf-walkthrough.md`.

---

## Technical Details

### 1. Style Changes in `style.py`
```css
/* Enlarged dropdown target for date picker */
QDateEdit::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 32px;
    border-left: 1px solid #334155;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

/* Status Badge sizing */
QLabel#statusBadge {
    padding: 2px 10px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 11px;
    min-height: 24px;
    max-height: 28px;
}
```

### 2. DeviceInfo Signal & Discovery in `workers.py`
In `DiscoveryWorker`:
- Add `signal_device_info = Signal(dict)`
- Query `GET /ISAPI/System/deviceInfo` on NVR host and emit metadata dictionary (e.g. `{"model": "...", "firmwareVersion": "..."}`).

### 3. Main Window Updates in `main_window.py`
- Header: `self.user_input.setMinimumWidth(115)`, `self.theme_btn.setFixedSize(32, 28)`.
- Left Panel: `self.camera_scroll.setMinimumHeight(240)`, group title `"Recording Time Window"`.
- Right Panel: Section headers added, console header aligned with `Live Console` and 24px Clear button.
- Footer: `self.footer_device_label` updated dynamically on connect/disconnect and device info discovery.

---

## Verification Plan
1. Unit tests: `uv run pytest tests/unit/test_ui.py`.
2. Full suite: `uv run pytest tests/unit tests/functional`.
3. Type checking: `uv run mypy src tests`.
4. Linting & Formatting: `uv run ruff check .` & `uv run ruff format --check .`.
