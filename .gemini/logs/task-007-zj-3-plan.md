# Plan: Task 007-zj-3 - Dynamic Dropdown Refresh on Click & Instant Keychain Loading

## 1. Requirement & Architectural Analysis

### Problem Statement
When the user clicks the right side (drop-down arrow/popup) of `host_input` or `user_input`, the items shown in the drop-down list must dynamically fetch the latest records from `QSettings` and OS Keychain in real-time (at the exact moment the dropdown is opened), rather than relying on stale cached items from application startup.

### Architectural Solution
1. **Dynamic Popup Refresh in `ProfileComboBox`**:
   - Extend `ProfileComboBox(QComboBox)` to override `showPopup()`.
   - When the user clicks the right side arrow, `showPopup()` triggers a pre-popup refresh hook.
   - Preserves the currently typed/active text in the line editor while rebuilding the dropdown items with the latest state from `QSettings`.
2. **Real-Time Host Dropdown Hook**:
   - `self.host_input.set_popup_callback(self._refresh_host_dropdown_items)`:
     - Pulls latest unique hosts from `get_saved_hosts_from_settings()`.
     - Refreshes `host_input` items on-the-fly.
3. **Real-Time User Dropdown Hook**:
   - `self.user_input.set_popup_callback(self._refresh_user_dropdown_items)`:
     - Reads current `host_input.text()`.
     - Pulls latest saved usernames for that host from `get_saved_usernames_from_settings(current_host)`.
     - Refreshes `user_input` items on-the-fly.
4. **Interactive Dropdown Selection (`activated`)**:
   - When a host is clicked from the dropdown (`host_input.activated`):
     - Sets the host text.
     - Restores matching port from `QSettings`.
     - Populates matching users in `user_input`.
     - Queries OS Keychain for `(host, user, port)` and immediately auto-fills `password_input` with `"🔑 Retrieved from OS Keychain"`.
   - When a username is clicked from the dropdown (`user_input.activated`):
     - Sets the user text.
     - Queries OS Keychain for `(host, user, port)` and immediately auto-fills `password_input` with `"🔑 Retrieved from OS Keychain"`.
5. **Disconnect Integration**:
   - Disconnect clears current inputs (`host_input.setEditText("")`, `user_input.setEditText("")`, `password_input.clear()`, console cleared, etc.).
   - When the user subsequently clicks the dropdown arrow on `Host` or `User`, `showPopup()` dynamically fetches and displays the saved profiles from `QSettings`/Keychain.

---

## 2. Target Files

### Files to Modify
- `src/hikvision_downloader/ui/main_window.py`:
  - Enhance `ProfileComboBox` to override `showPopup()` and support `set_popup_callback()`.
  - Add `_refresh_host_dropdown_items()` and `_refresh_user_dropdown_items()`.
  - Wire `activated` signal handlers on `host_input` and `user_input` for immediate OS Keychain credential loading.
- `tests/unit/test_ui.py`:
  - Add tests verifying `ProfileComboBox.showPopup()` triggers dynamic dropdown refresh with latest `QSettings` state.
  - Test dropdown selection (`activated`) immediately loads credentials from OS Keychain.

---

## 3. Verification & Testing Plan
- `uv run pytest tests/unit/test_ui.py`
- `uv run mypy src tests`
- `uv run ruff check .`
- Create walkthrough document at `.gemini/logs/task-007-zj-3-walkthrough.md`
