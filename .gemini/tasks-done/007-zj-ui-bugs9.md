MASTER ARCHITECTURAL & UI REFACTOR: NATIVE OS KEYCHAIN (NO PROFILES.JSON), QSETTINGS, HIGH-CONTRAST SUMMARY BADGES & ERGONOMIC CLEANUP

Refactor `src/hikvision_downloader/ui/` adhering strictly to `.gemini/rules/2-security.md` and `.gemini/rules/4-coding-standards.md` (100% type annotations, zero bare `Any`).

### 1. Eliminate `profiles.json` and Migrate to Native QSettings
- Deprecate and completely remove `~/.hikvision-downloader/profiles.json` and `profiles.py`.
- Desktop app history (known hosts, ports, usernames, and window state) must use Qt's native cross-platform storage:
  `settings = QSettings("Arivedha", "HikVisionDownloader")`
  - macOS: `~/Library/Preferences/com.arivedha.HikVisionDownloader.plist`
  - Windows: `HKEY_CURRENT_USER\Software\Arivedha\HikVisionDownloader`
  - Linux: `~/.config/Arivedha/HikVisionDownloader.conf`
- NEVER store plain-text passwords or secret keys in `QSettings`. Only store metadata (e.g. `recent_hosts: list[str]`, `recent_users: list[str]`).

### 2. Native OS Keychain Storage & Interactive Auto-Fill (`keychain.py`)
- Clean up `keychain.py` to use proper `keyring` operations:
  - Account key convention: `f"{username}@{host}:{port}"`
  - When saving: `keyring.set_password("hikvision_downloader", f"{username}@{host}:{port}", password)`
  - When retrieving:
    - Look up exact account `f"{username}@{host}:{port}"`.
    - If `username` is blank, discover matching credentials for `@{host}:{port}`.
    - Return `(username, password)` or `None`.
  - Never swallow errors silently; log explicit diagnostics.
- In `main_window.py`:
  - Hook interactive auto-fill events on both `self.host_input` and `self.user_input`:
    - `currentIndexChanged`
    - `lineEdit().editingFinished`
  - When the user selects or types a known host/user, query Keychain immediately:
    - If found: auto-fill `self.password_input`, check `Save in Keychain`, set tooltip `"🔑 Retrieved from OS Keychain"`, and log `[INFO] Loaded password from OS Keychain for <user>@<host>:<port>`.
    - If not found: clear `self.password_input` cleanly without error alerts.
  - On `self.host_input` and `self.user_input`, add `customContextMenuRequested` with an action:
    - `"Remove Stored Profile & Keychain Credentials"`
    - Deletes the entry from OS Keychain via `keyring.delete_password(...)`, removes it from `QSettings`, and refreshes the combobox items.

### 3. Redesign Segment Summary Metrics into High-Contrast Badges
- In `main_window.py` inside `_build_recordings_view_panel()` and `_on_table_data_changed()`:
  - Replace the dim, easily missed `self.summary_label` with two styled metric pills positioned on the bottom bar under the table:
    - **Badge 1 (Discovered Segments)**:
      - Text: `723 Segments Discovered · 80.12 GB`
      - Style: `background-color: #1E293B; color: #E2E8F0; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; border: 1px solid #334155;`
    - **Badge 2 (Selected Segments)**:
      - Text: `✓ 723 Selected · 80.12 GB`
      - Style when selected: `background-color: #0F2D37; color: #38BDF8; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; border: 1px solid #1E6B7B;`
      - Style when 0 selected: `background-color: #1E293B; color: #64748B; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; border: 1px solid #334155;`

### 4. Table Column Layout & Naming Verification
- Keep native vertical headers hidden on BOTH tables: `table.verticalHeader().setVisible(False)`.
- Enforce identical column structures:
  - Column 0: `[✓]` (centered checkbox, width `34px`, header checkbox toggle).
  - Column 1: `#` (row index, width `40px`, centered text).
  - Column 2+: Data columns.
- Ensure camera names strictly reflect discovery without alterations (e.g. `D1 MainGate`, `D4 FirstFL`), with zero synthetic `"CH"` prefixes.

### 5. Verification Suite
- Verify that `~/.hikvision-downloader` is never created.
- Confirm changing host or username immediately pulls the matching password from the OS Keychain.
- Confirm right-clicking a saved credential allows full deletion from both Keychain and `QSettings`.
- Confirm segment summary renders as high-contrast twin badges beneath the recordings table.
- Run `uv run pytest tests/unit/test_ui.py`.
- Run `uv run mypy src tests` (100% strict type safety).
- Run `uv run ruff check .`.
- Present the updated walkthrough in `.gemini/logs/task-007-zk-walkthrough.md`.