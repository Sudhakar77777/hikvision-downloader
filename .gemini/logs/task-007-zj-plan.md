# Plan: Task 007-zj - Master Architectural & UI Refactor

## 1. Requirement & Architectural Analysis

### Objective
Complete the master architectural refactor of the desktop UI (`src/hikvision_downloader/ui/`) by:
1. Eliminating file-based `profiles.json` and `profiles.py`, replacing them with Qt's native cross-platform `QSettings("Arivedha", "HikVisionDownloader")`.
2. Ensuring `~/.hikvision-downloader` is never created and passwords are never stored in plain-text `QSettings`.
3. Upgrading `keychain.py` to use proper `keyring` operations with account key format `f"{username}@{host}:{port}"`, supporting reactive auto-fill on host/user change, and full credential deletion via context menu.
4. Redesigning table segment summary metrics into high-contrast twin badge pills (`discovered_badge` and `selected_badge`).
5. Ensuring table column formatting and clean camera names (no synthetic `"CH"` prefixes) with hidden vertical headers.
6. Ensuring 100% strict type safety (zero bare `Any`, all typed parameters and return values), `ruff` conformance, and comprehensive unit tests.

---

## 2. Target Files

### Files to Remove
- `src/hikvision_downloader/ui/profiles.py` (deprecated and removed; migrated to `settings.py`)

### Files to Create
- `src/hikvision_downloader/ui/settings.py` (pure `QSettings`-backed profile metadata and window state persistence)
- `.gemini/logs/task-007-zj-plan.md` (this planning document)
- `.gemini/logs/task-007-zj-walkthrough.md` / `.gemini/logs/task-007-zk-walkthrough.md` (walkthrough document)

### Files to Modify
- `src/hikvision_downloader/ui/__init__.py`: Update exports to remove `profiles.py` and export `settings.py` helpers.
- `src/hikvision_downloader/ui/keychain.py`: Standardize on `f"{username}@{host}:{port}"` account key, robust error handling with diagnostic logs, credential auto-discovery, and full deletion.
- `src/hikvision_downloader/ui/main_window.py`:
  - Replace `profiles.py` imports with `settings.py`.
  - Connect reactive auto-fill signals (`currentIndexChanged`, `lineEdit().editingFinished`).
  - Add custom context menus on `host_input` and `user_input` for "Remove Stored Profile & Keychain Credentials".
  - Replace `summary_label` with high-contrast twin metric badges: `discovered_badge` and `selected_badge`.
  - Persist and restore window geometry/state using `QSettings`.
- `tests/unit/test_ui.py`:
  - Update tests to verify `settings.py` (QSettings behavior with isolated test settings format), `keychain.py`, twin badges, reactive auto-fill, context menu deletion, and model column properties.

---

## 3. Proposed Logic & Implementation Details

### A. Settings Management (`src/hikvision_downloader/ui/settings.py`)
- Define `get_settings() -> QSettings`: returns `QSettings("Arivedha", "HikVisionDownloader")`.
- Store non-sensitive metadata only:
  - `recent_hosts`: `list[str]` (MRU ordered list of hostnames/IPs)
  - `profiles`: list of dicts (or JSON serialized string) with fields `host`, `port`, `username`, `last_used`.
- Implement helpers:
  - `save_profile_to_settings(host: str, port: int = 80, username: str = "admin", settings: QSettings | None = None) -> None`
  - `delete_profile_from_settings(host: str, port: int = 80, username: str = "admin", settings: QSettings | None = None) -> bool`
  - `get_saved_hosts_from_settings(settings: QSettings | None = None) -> list[str]`
  - `get_saved_usernames_from_settings(host: str | None = None, settings: QSettings | None = None) -> list[str]`
  - `save_window_state(window: QMainWindow, settings: QSettings | None = None) -> None`
  - `restore_window_state(window: QMainWindow, settings: QSettings | None = None) -> bool`

### B. OS Keychain Management (`src/hikvision_downloader/ui/keychain.py`)
- Primary service: `hikvision_downloader`
- Account format helper: `format_account_key(username: str, host: str, port: int = 80) -> str` (`f"{username}@{host}:{port}"`).
- Parsing helper: `parse_account_key(account: str) -> tuple[str, str, int] | None` (parses `user@host:port` and fallback variations).
- Functions:
  - `save_nvr_password(host: str, username: str, password: str, port: int = 80) -> bool`
  - `get_nvr_password(host: str, username: str, port: int = 80) -> str | None`
  - `get_nvr_credential(host: str, username: str = "", port: int = 80) -> tuple[str, str] | None`
  - `delete_nvr_password(host: str, username: str, port: int = 80) -> bool`
- Explicit warning/info diagnostics when querying, saving, or deleting credentials.

### C. Main Window Integration (`src/hikvision_downloader/ui/main_window.py`)
- **Reactive Keychain Auto-Fill**:
  - `host_input.currentIndexChanged` and `user_input.currentIndexChanged` trigger keychain lookup.
  - `lineEdit().editingFinished` triggers lookup on manual text editing.
  - When credentials match:
    - Auto-fill `password_input`.
    - Check `Save in Keychain`.
    - Tooltip: `"🔑 Retrieved from OS Keychain"`.
    - Log: `[INFO] Loaded password from OS Keychain for <user>@<host>:<port>`.
  - When not found:
    - Clear `password_input` cleanly with empty tooltip.
- **Context Menu Credential Purge**:
  - Add `customContextMenuRequested` on `host_input`, `user_input`, and their `lineEdit()`.
  - Action: `"Remove Stored Profile & Keychain Credentials"`.
  - Invokes `delete_nvr_password(...)`, `delete_profile_from_settings(...)`, clears inputs, and repopulates comboboxes.
- **High-Contrast Twin Badges**:
  - In `_build_recordings_view_panel()`, create `self.discovered_badge` and `self.selected_badge`.
  - Badge 1 (Discovered):
    - Text: `{count} Segments Discovered · {size}`
    - CSS: `background-color: #1E293B; color: #E2E8F0; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; border: 1px solid #334155;`
  - Badge 2 (Selected):
    - When selected > 0:
      - Text: `✓ {count} Selected · {size}`
      - CSS: `background-color: #0F2D37; color: #38BDF8; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; border: 1px solid #1E6B7B;`
    - When 0 selected:
      - Text: `0 Selected · 0 B`
      - CSS: `background-color: #1E293B; color: #64748B; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; border: 1px solid #334155;`
  - Update `_on_table_data_changed()` and `_disconnect_session()` to update twin badges.

---

## 4. Verification & Testing Plan

1. **Unit Tests (`uv run pytest tests/unit/test_ui.py`)**:
   - `test_settings_storage`: Verify `QSettings` read/write/delete without file artifacts.
   - `test_keychain_operations`: Test `f"{username}@{host}:{port}"` key format, retrieval, auto-discovery, and error handling.
   - `test_twin_summary_badges`: Verify badge text and styles under 0 segments, discovered segments, and active selections.
   - `test_reactive_autofill_and_context_menu`: Verify reactive lookup and context-menu deletion from both Keychain and `QSettings`.
   - Run all unit and integration test suites: `uv run pytest`.
2. **Type Safety & Linting**:
   - `uv run mypy src tests` (100% strict type safety check, 0 errors).
   - `uv run ruff check .` (0 linting or formatting errors).
3. **Walkthrough Document**:
   - Write `.gemini/logs/task-007-zj-walkthrough.md` detailing all implemented changes and test results.
