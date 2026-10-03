# Walkthrough: Dynamic Live Dropdown Refresh & Instant OS Keychain Loading (Sub-task 007-zj-3)

## Summary of Changes

Sub-task `007-zj-3` resolves the dropdown list and OS Keychain loading behavior when clicking the right-side drop-down arrow of `host_input` or `user_input` (especially after Disconnect).

### 1. Dynamic Dropdown Popup Refresh via `ProfileComboBox.showPopup()`
- Subclassed `ProfileComboBox(QComboBox)` now provides `set_popup_callback(fn)` and overrides `showPopup()`.
- When the user clicks the drop-down arrow, `showPopup()` runs the callback immediately before displaying the popup list:
  - **Host Dropdown**: Queries `get_saved_hosts_from_settings()` to dynamically load all saved host entries from `QSettings`.
  - **User Dropdown**: Queries `get_saved_usernames_from_settings(host)` to dynamically load all saved usernames associated with the currently chosen host.
- Both methods block signals during dropdown list rebuilding and preserve current editor text so opening the popup does not accidentally wipe typed input.

### 2. Instant OS Keychain Loading on Dropdown Selection (`activated` signal)
- Connected `host_input.activated` to `_on_host_dropdown_selected`:
  - When the user picks a host from the dropdown list, it automatically looks up the matching profile port, refreshes the username dropdown for that host, sets the username, and immediately performs `_auto_lookup_keychain(allow_user_autodiscovery=True)`.
  - The password is instantaneously loaded from OS Keychain and populated into `password_input` with the `"🔑 Retrieved from OS Keychain"` tooltip.
- Connected `user_input.activated` to `_on_user_dropdown_selected`:
  - When the user picks a username from the dropdown list, it immediately queries `get_nvr_password(host, user, port)` from OS Keychain and updates the password field.

---

## Verification Results

### Unit & Integration Tests
- `uv run pytest tests/unit/test_ui.py`: **28 passed in 0.96s**
  - Verified `test_profile_combobox_dynamic_popup_callback`: confirmed popup callback execution upon opening dropdown.
  - Verified `test_dropdown_dynamic_refresh_and_keychain_loading_after_disconnect`: confirmed full disconnect purges state, subsequent host dropdown click dynamically fetches saved hosts from settings, and selecting an item immediately populates host, port, user, and password from OS Keychain.
- Full test suite: **162 passed, 1 skipped** (151 non-integration passed in 0.90s).

### Static Analysis & Type Checking
- `uv run mypy src tests`: **Success: no issues found in 41 source files** (strict mode, 100% type annotations).
- `uv run ruff check .`: **All checks passed!**
