REFINE CAMERA LIST TABLE, STANDARDIZE TERMINOLOGY & IMPLEMENT ROBUST KEYCHAIN LOOKUP

Execute these targeted fixes across `src/hikvision_downloader/ui/` adhering strictly to `.gemini/rules/2-security.md` and `.gemini/rules/4-coding-standards.md`.

### 1. Rename Section & Terminology
- In `main_window.py`:
  - Rename the section header from `CAMERA CHANNELS & STREAM` strictly to **`CAMERAS & STREAMS`**.
  - Remove all occurrences of "Channel" from operator-facing labels. The list represents "Cameras" with their hardware models.

### 2. Left Panel: Replace Custom Widget Scroll Area with a Compact QTableView
- Replace the ad-hoc `CameraRowWidget` container in `_build_camera_group()` with a clean, compact `QTableView` (or `QTableWidget`) that visually matches the right-hand `RECORDINGS / VIDEO FILES` table:
  - Columns:
    1. Selection Checkbox (`[✓]`, width `32px`, centered header toggle).
    2. Number `#` (`1`, `2`, `3`... row index).
    3. Camera Name (`CH01 MainGate`, `CH02 MainEntrance`, etc.).
    4. Hardware Model (`DS-2CD1023G2-LIU`).
  - Set compact row height: `table.verticalHeader().setDefaultSectionSize(22)`.
  - Enable alternating row colors and table border styling matching the right operational table.
  - Implement full height stretching so the table cleanly occupies the vertical space down to the `Stream Quality` selector with zero awkward empty gaps.
  - Wire `Select All` and `Deselect` buttons directly to the model's check states so clicking "Deselect" immediately unchecks all rows.

### 3. Fix Silent Keychain Failures & Interactive Credential Retrieval
- In `src/hikvision_downloader/ui/keychain.py`:
  - Review all try/except blocks: NEVER silently swallow errors with `except Exception: pass`.
  - Log explicit diagnostic messages (e.g. `logger.debug("Keychain query for %s returned no entry", account_key)`).
  - Support flexible account key matching:
    - Primary key format: `f"{host}:{port}:{username}"`
    - Fallback key format: `f"{host}:{username}"`
- In `src/hikvision_downloader/ui/main_window.py`:
  - Implement reactive auto-fill:
    ```python
    self.host_input.editingFinished.connect(self._auto_lookup_keychain)
    self.port_input.editingFinished.connect(self._auto_lookup_keychain)
    self.user_input.editingFinished.connect(self._auto_lookup_keychain)
    ```
  - In `_auto_lookup_keychain()`:
    - Read current `host`, `port`, and `user`.
    - If `user` and `host` are present, query `get_nvr_password(host, user, port)`.
    - If found, populate `self.password_input.setText(password)` and set `self.remember_cb.setChecked(True)`.
    - Display a key icon 🔑 or tooltip on the password field: `"Credentials retrieved from OS Keychain"`.
    - If not found, clear the password input and do not log misleading "Retrieved stored credentials" messages.
  - Fix the mismatch where keychain loaded `remotebuddy` while the UI displayed `admin`. The user input field MUST update to match the account key loaded from keychain.

### 4. Verification
- Confirm that the left camera list renders as a tight, numbered table matching the style of the recordings table.
- Confirm that typing an existing username and tabbing out immediately fills the password from Keychain.
- Run `uv run pytest tests/unit/test_ui.py`.
- Run `uv run mypy src tests` (100% strict type safety).
- Run `uv run ruff check .`.
- Present the updated walkthrough in `.gemini/logs/task-007-zh-walkthrough.md`.