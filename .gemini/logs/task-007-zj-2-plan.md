# Plan: Task 007-zj-2 - Complete Disconnect UI Purge & Username Deletion Fix

## 1. Requirement Analysis & Root Cause

### Issue 1: Comprehensive Disconnect State Reset
On clicking the "Disconnect" button, the application must perform a complete reset to initial pristine state without retaining any residual data across any panel:
1. **Live Activity Console**:
   - `self.console_log.clear()` (completely empty console text log).
2. **Connection Form Inputs**:
   - `self.host_input`: cleared / set to empty text (`self.host_input.clear()`, `self.host_input.setEditText("")`).
   - `self.user_input`: cleared / set to empty text (`self.user_input.clear()`, `self.user_input.setEditText("")`).
   - `self.password_input`: cleared (`self.password_input.clear()`, tooltip cleared).
   - `self.port_input`: reset to default (`80`).
   - `self.remember_cb`: reset to checked (`True`).
3. **Recording Time Window**:
   - `self.date_picker`: reset to current system date and calendar date highlights cleared.
   - `self.start_hh_combo`: reset to `"00"`.
   - `self.start_mm_combo`: reset to `"00"`.
   - `self.end_hh_combo`: reset to `"23"`.
   - `self.end_mm_combo`: reset to `"59"`.
4. **Discovered Sources & Segments**:
   - `self._discovered_cameras.clear()`
   - `self._cameras_table_model.clear()`
   - `self.cameras_stack.setCurrentIndex(0)`
   - `self.stream_combo.clear()` & `self.stream_combo.setEnabled(False)`
   - `self._table_model.clear()`
   - `self.discovered_badge` reset to `"0 Segments Discovered · 0 B"`
   - `self.selected_badge` reset to `"0 Selected · 0 B"`
   - `self.overall_progress_bar.setValue(0)`
   - `self.progress_readout.setText("[ 0% ]  Idle  |  0.0 Mbps  |  Elapsed: 00:00  |  ETA: --:--")`
   - `self.footer_device_label.setText("Disconnected · Ready")`
   - Action buttons (`search_btn`, `start_download_btn`, `abort_btn`) disabled.

### Issue 2: Username Deletion Block (Auto-Discovery Collision)
**Root Cause**:
- When the user edited or cleared the username field in `self.user_input`, `_auto_lookup_keychain()` was triggered with `user=""`.
- Because `user` was empty, `_auto_lookup_keychain()` executed generic host credential discovery (`get_nvr_credential(host, "", port)`), which found a stored credential for that host and immediately called `self.user_input.setText(matched_user)`.
- This created an inescapable loop preventing the user from clearing or changing the username.
- In addition, `_populate_profile_combos()` unconditionally forced `NVR_USERNAME or "admin"` back into the combo box even if the entry was deleted or cleared.

**Resolution**:
- Update `_auto_lookup_keychain(allow_user_autodiscovery: bool = False)`:
  - When the user edits `user_input`, only query the password for the specifically entered username. If empty, simply clear `password_input` without overwriting `user_input`.
  - Only allow auto-discovery of username when switching `host_input` or during initial startup.
- Update `_populate_profile_combos(preserve_current: bool = False)` to avoid forcing default username if user has deleted or cleared it.
- In `delete_profile_from_settings`, ensure case-insensitive matching for both `host` and `username`.

---

## 2. Target Files

### Files to Modify
- `src/hikvision_downloader/ui/main_window.py`:
  - Update `_disconnect_session()` to clear all input fields, time window widgets, and live console.
  - Update `_auto_lookup_keychain()` with `allow_user_autodiscovery` parameter to prevent username auto-fill recursion when deleting/typing username.
  - Update `_remove_current_profile_and_credentials()` and `_populate_profile_combos()`.
- `src/hikvision_downloader/ui/settings.py`:
  - Ensure case-insensitive username and host matching in `delete_profile_from_settings`.
- `tests/unit/test_ui.py`:
  - Update `test_disconnect_session_complete_purge` to verify all inputs, time widgets, and console are empty upon disconnect.
  - Add test verifying username can be cleared/deleted without being overwritten.

---

## 3. Verification & Testing Plan
- Run `uv run pytest tests/unit/test_ui.py`
- Run `uv run mypy src tests`
- Run `uv run ruff check .`
- Create walkthrough at `.gemini/logs/task-007-zj-2-walkthrough.md`
