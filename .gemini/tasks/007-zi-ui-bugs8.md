CRITICAL UI OVERHAUL: REMOVE CAMERA NAME OVERRIDE, ENFORCE TABLE COLUMN SYMMETRY, DISCONNECT PURGE & INTERACTIVE KEYCHAIN

Refactor `src/hikvision_downloader/ui/` adhering strictly to `.gemini/rules/2-security.md` and `.gemini/rules/4-coding-standards.md`.

### 1. Remove "CH" Camera Name Fudging (Use Real NVR Channel Names)
- In `src/hikvision_downloader/ui/models.py` (and wherever the camera table is populated):
  - REMOVE any string manipulation or hack that prefixes or replaces camera names with "CH01", "CH02", etc.
  - Display the camera's exact name as returned from the NVR/ISAPI discovery:
    - Real name: `camera.name` (e.g., `D1 MainGate`, `D4 FirstFL`, `D9 TerraceDoor`, etc.).
    - Never alter or synthesize channel name strings.

### 2. Enforce Exact Visual & Column Symmetry Across Both Tables
- Look at `src/hikvision_downloader/ui/models.py` and `main_window.py`:
  - Both Left (Cameras) and Right (Recordings) tables must follow the exact same visual structure:
    - Hide native vertical headers on BOTH tables:
      `table.verticalHeader().setVisible(False)`
    - **Column 0**: Selection Checkbox `[✓]` (width `34px`, centered, with a header toggle checkbox).
    - **Column 1**: Row Number `#` (width `40px`, centered text: `1`, `2`, `3`...).
    - **Column 2+**: Data columns.
  - **Left Table Columns**:
    `[✓]` | `#` | `Camera Name` | `Hardware Model`
  - **Right Table Columns**:
    `[✓]` | `#` | `Camera` | `Stream` | `File Name` | `Start Time` | `End Time` | `Size` | `Status`
  - Ensure row heights match exactly (`table.verticalHeader().setDefaultSectionSize(22)`).

### 3. Complete State Purge on Disconnect
- In `main_window.py` inside `_disconnect_session()`:
  - Disconnect active workers and clear session objects.
  - Clear the Left Camera Table and restore the centered placeholder label:
    `"No cameras discovered. Click 'Connect' to discover cameras."`
  - Clear the Right Files Table (0 rows) and reset summary:
    `"0 segments discovered (0 B) | 0 selected (0 B)"`.
  - Disable Action Buttons: `START BATCH DOWNLOAD` and `SEARCH RECORDINGS`.
  - Reset Stream Quality dropdown to blank/disabled.
  - Append a clean divider to the Live Console:
    `[INFO] Session disconnected. Ready.`
  - Clear the `Password:` field completely (`self.password_input.clear()`).

### 4. Interactive OS Keychain & Saved NVR Profiles
- Eliminate silent failures and hardcoded account mismatches:
  - Create a profile storage helper in `src/hikvision_downloader/ui/profiles.py`:
    - Save known `(host, port, username)` tuples to `~/.hikvision-downloader/profiles.json`.
  - In `main_window.py`:
    - Change `self.host_input` and `self.user_input` to editable `QComboBox` (or `QLineEdit` with `QCompleter`).
    - Populate them on startup from `saved_profiles.json`.
    - Connect `currentIndexChanged` / `editingFinished`:
      - When an operator selects or types a host/user, query `get_nvr_password(host, username, port)` from `keychain.py`.
      - If found:
        - Populate `password_input` with the retrieved password.
        - Check `Save in Keychain`.
        - Log: `[INFO] Loaded password from OS Keychain for <user>@<host>:<port>`.
      - If not found:
        - Clear `password_input`.
        - Log: `[DEBUG] No keychain password entry found for <user>@<host>:<port>`.
    - When "Connect" succeeds and "Save in Keychain" is checked:
      - Persist password to OS Keychain via `keyring.set_password("hikvision_downloader", f"{host}:{port}:{username}", password)`.
      - Save the profile to `saved_profiles.json` and update the combobox dropdown history.
    - If `keyring` raises any error, NEVER catch silently:
      - Display a clear warning in the console: `[ERROR] OS Keychain access failed: <error_details>`.

### 5. Verification
- Confirm camera names show their actual NVR names (`D1 MainGate`, `D4 FirstFL`, etc.) without "CH" prefixes.
- Confirm both tables share `[✓]` as column 0 and `#` as column 1 with native vertical headers hidden.
- Confirm selecting/typing known credentials immediately loads the password from Keychain.
- Confirm clicking "Disconnect" cleanly resets tables, clears password, and restores placeholders.
- Run `uv run pytest tests/unit/test_ui.py`.
- Run `uv run mypy src tests` (100% strict type safety).
- Run `uv run ruff check .`.
- Present the updated walkthrough in `.gemini/logs/task-007-zi-walkthrough.md`.