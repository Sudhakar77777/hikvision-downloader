CRITICAL UI REFACTOR: EMBEDDED SECTION HEADERS, VERTICAL PROGRESS BAR, COMPLETE DISCONNECT PURGE & TOP ALIGNMENT

Execute these refinements across `src/hikvision_downloader/ui/` adhering strictly to `.gemini/rules/4-coding-standards.md` (100% type annotations).

### 1. Increase Window Geometry & Splitter Stability
- In `main_window.py`:
  - Increase default launch height: `resize(1340, 920)` with minimum size `1200x820` (calculating available screen geometry with `QApplication.primaryScreen().availableGeometry()`).
  - Left panel `minimumWidth=410`.
  - Increase Camera scroll area `minimumHeight` to `280px` to naturally absorb the additional window height without leaving empty voids.

### 2. Section Headers: Embed Cleanly Inside Card Containers (Left & Right Consistency)
- Remove all external floating section headers from the Left Panel.
- Structure both panels symmetrically with embedded flat titles:
  - **Left Card 1 (Top)**: Clean flat header inside the card layout:
    `QLabel("CAMERA CHANNELS & STREAM")` styled with `font-size: 11px; font-weight: bold; color: #38BDF8; background: transparent; border: none; padding-bottom: 6px;`
  - **Left Card 2 (Bottom)**: Clean flat header inside the card layout:
    `QLabel("RECORDING TIME WINDOW")` matching the exact same typography.
  - **Spacing**: Add an explicit `addSpacing(10)` or `margin-top: 10px` above `Stream Quality:` so it does not crowd the bottom of the camera list.

### 3. Top Connection Bar: Align Status Badge & Theme Button Symmetrically
- Inspect `status_badge` and `theme_btn` vertical layout inside `headerFrame`:
  - Ensure both widgets have identical fixed heights (`28px`) and matching vertical layout alignments (`alignment=Qt.AlignmentFlag.AlignVCenter`).
  - Status Badge: `setFixedHeight(28)`, `padding: 2px 8px; font-size: 11px; border-radius: 6px;`
  - Theme Button: `setFixedSize(36, 28)`, clean centered icon (`☀️` / `🌙`), transparent or subtle card border, zero horizontal margin clipping.

### 4. Complete Session Purge on Disconnect
- In `_disconnect_session()`:
  - Completely destroy and clear all `CameraRowWidget` children from the camera scroll area layout (`while item := layout.takeAt(0): if w := item.widget(): w.deleteLater()`).
  - Re-display the clean placeholder label: `"No cameras discovered. Click 'Connect' to discover channels."`
  - Reset `RecordingsTableModel` to 0 rows (`model.clear()` or `model.set_recordings([])`).
  - Reset segment counter text: `"0 segments discovered (0 B) | 0 selected (0 B)"`.
  - Reset Stream Quality dropdown back to its default initial state.
  - Reset progress bar to `0%`, transfer status text to `"Idle"`, and throughput to `"0.0 Mbps"`.
  - Revert footer status strictly to `"Disconnected · Ready"`.

### 5. Live Console Header & Dedicated Progress Bar
- Restructure the Live Console section into a clean 3-tier hierarchy:
  - **Tier 1 (Header Line)**:
    `[ LIVE CONSOLE ]` (flat section title on the left)  -------------------  `[ Clear ]` button on the far right.
  - **Tier 2 (Dedicated Status & Progress Bar Line)**:
    - Sits directly beneath the header line and spans the full card width.
    - Left side: Clean styled `QProgressBar` (height `8px` or `10px`, radius `4px`).
    - Right side: Status readout: `[ 0% ]  Idle  |  0.0 Mbps  |  Elapsed: 00:00  |  ETA: --:--`
  - **Tier 3 (Terminal Console)**:
    - Monospaced `QPlainTextEdit` terminal area below the progress bar.

### 6. Verification
- Confirm that logging in, loading cameras, and clicking "Disconnect" cleanly resets the GUI to its pre-login state without orphaned camera rows.
- Verify `status_badge` and `theme_btn` share identical heights and vertical centers.
- Run `uv run pytest tests/unit/test_ui.py`.
- Run `uv run mypy src tests` (confirm 100% strict type checking).
- Run `uv run ruff check .`.
- Document all fixes in `.gemini/logs/task-007-zg-walkthrough.md`.

### 7. Interactive Keychain Retrieval & Reactive Auto-Fill
- In `src/hikvision_downloader/ui/main_window.py`:
  - Connect `editingFinished` on both `host_input` and `user_input` to an auto-fill handler:
    ```python
    self.host_input.editingFinished.connect(self._on_connection_field_changed)
    self.user_input.editingFinished.connect(self._on_connection_field_changed)
    ```
  - When `_on_connection_field_changed()` fires:
    - Extract current `host = self.host_input.text().strip()`, `port = self.port_input.value()`, `user = self.user_input.text().strip()`.
    - Query `get_nvr_password(host, user, port)` from `keychain.py`.
    - If a stored password is found:
      - Automatically populate `self.password_input.setText(stored_password)`.
      - Check `self.remember_cb.setChecked(True)`.
      - Log to console: `[INFO] Retrieved stored credentials from OS Keychain for <user>@<host>:<port>`.
  - Provide a visual cue: when credentials are auto-filled from Keychain, show a subtle key icon 🔑 or tooltip on the password input ("Loaded from OS Keychain").