POLISH PASS: TOP BAR ALIGNMENT, SECTION HEADERS, LIVE HARDWARE STATUS & ERGONOMIC FIXES

Execute these specific UI refinements in `src/hikvision_downloader/ui/` adhering to `.gemini/rules/4-coding-standards.md`.

### 1. Top Connection Bar Refinements
- User Field Width: Increase `user_input` minimum width from 90px to `115px` so usernames (e.g. "remotebuddy") are not cramped.
- Focus Clearing: After a successful connection in `_on_auth_success()`, call `self.host_input.clearFocus()` and set focus to `self.search_btn` so the text cursor doesn't linger inside the Host box.
- Vertical Sizing & Alignment:
  - Give both `status_badge` and `theme_btn` matching heights (`28px`), centered vertically:
    - Status Badge: `height: 28px; line-height: 28px; padding: 2px 10px; font-size: 11px;`
    - Theme Button: `fixedSize(32, 28)`.

### 2. Left Panel: Camera List, Naming & Date Selector
- Camera Scroll Area Geometry:
  - Increase the camera list container's minimum height to `240px` and remove restrictive maximum height clamping so it utilizes empty vertical space cleanly.
- Fix Deselect Button:
  - Ensure clicking "Deselect" iterates through all `CameraRowWidget` instances and explicitly sets `row.checkbox.setChecked(False)`.
- Show Camera Hardware Model:
  - When populating cameras, display the hardware model if available:
    e.g., `D1 MainGate (DS-2CD2143G0-I)` or `D1 MainGate`.
- Label Renaming:
  - Change section title `INVESTIGATION TIME WINDOW` strictly to **`RECORDING TIME WINDOW`**.
- Date Picker Dropdown Target:
  - In `style.py`, enlarge the clickable arrow area for `QDateEdit`:
    ```css
    QDateEdit::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 32px;
        border-left: 1px solid #1E293B;
    }
    ```

### 3. Right Panel: Section Headers & Live Console Clean Up
- Add Section Header 1: Above the recordings table, add a clean section title: **`RECORDINGS / VIDEO FILES`**.
- Add Section Header 2: Above the output path line, add a clean section title: **`DOWNLOAD SETTINGS`**.
- Live Console Header Refinements:
  - Rename label `Live Activity Console` strictly to **`Live Console`**.
  - Symmetrically align the console header items in a single centered `QHBoxLayout`:
    `[Live Console Label]  [Progress Bar: 0%]  [Idle | 0.0 Mbps | Elapsed: 00:00]  [Clear Button]`
  - Match the `Clear` button height (`24px`) cleanly with adjacent text widgets.

### 4. Dynamic NVR Hardware Information in Footer
- In the bottom footer frame, replace the static `"v0.1.0-alpha · Automated ISAPI Engine"` text with dynamic NVR details:
  - When disconnected: `"Disconnected · Ready"`
  - When connected: Extract device metadata from the NVR session / DeviceInfo (e.g. Model, Firmware) and display:
    `Model: <model>  |  Firmware: <firmware>  |  Active Channels: <count>`
  - Fall back gracefully to `Connected: <host> (<count> Channels)` if `DeviceInfo` metadata is pending.

### 5. Verification
- Run `uv run pytest tests/unit/test_ui.py`.
- Run `uv run mypy src tests` (100% strict type safety).
- Run `uv run ruff check .`.
- Present the changes and verification output in `.gemini/logs/task-007-zf-walkthrough.md`.