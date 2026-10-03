# Walkthrough: Task 007-zj - Master Architectural & UI Refactor

## 1. Summary of Changes Implemented

### Phase 2 Implementation Summary

| Component | Target File | Status | Description |
|---|---|---|---|
| **Elimination of `profiles.json`** | `src/hikvision_downloader/ui/profiles.py` | **Removed** | Deprecated and deleted file-based profile storage (`profiles.py`) and eliminated all references to `~/.hikvision-downloader/profiles.json`. |
| **Native `QSettings` Engine** | [`settings.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/settings.py) | **Created** | Implemented cross-platform persistence using `QSettings("Arivedha", "HikVisionDownloader")`. Safely persists non-sensitive profile metadata (`host`, `port`, `username`, `last_used`) and window geometry without storing plain-text credentials. |
| **Package Exports** | [`__init__.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/__init__.py) | **Updated** | Exported `settings.py` functions and models, removing deprecated `profiles.py` symbols. |
| **OS Keychain Refactor** | [`keychain.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/keychain.py) | **Updated** | Standardized account key format to `f"{username}@{host}:{port}"`. Added support for credential discovery, fallback legacy keys, and explicit diagnostic logging. |
| **Reactive Auto-Fill & Context Menu** | [`main_window.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py) | **Updated** | Wired `currentIndexChanged` and `lineEdit().editingFinished` for reactive OS Keychain lookups. Added right-click context menu `"Remove Stored Profile & Keychain Credentials"` on host and user inputs to purge credentials from Keychain and `QSettings`. |
| **High-Contrast Metric Badges** | [`main_window.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py) | **Updated** | Replaced dim `summary_label` with two styled metric pills (`discovered_badge` and `selected_badge`) featuring dynamic styling based on selection state. |
| **Window State Persistence** | [`main_window.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/src/hikvision_downloader/ui/main_window.py) | **Updated** | Restores and persists window geometry automatically on startup and shutdown using `QSettings`. |
| **Unit Test Suite** | [`tests/unit/test_ui.py`](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/tests/unit/test_ui.py) | **Updated** | Updated test suite to validate `settings.py`, `keychain.py`, twin high-contrast badges, reactive auto-fill, and context menu deletion. |

---

## 2. Verification Results

### A. Test Suite (`uv run pytest`)
```
============================= test session starts ==============================
platform darwin -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /Volumes/MinionDev/Workspace/CCTV/hikvision-downloader
configfile: pyproject.toml
testpaths: tests
plugins: mock-3.16.0
collected 160 items

tests/functional/test_cancellation.py ....                               [  2%]
tests/functional/test_concurrent_downloads.py .....                      [  5%]
tests/functional/test_download_engine.py ..........                      [ 11%]
tests/integration/test_cli_commands.py ....s                             [ 15%]
tests/integration/test_live_nvr.py .......                               [ 19%]
tests/unit/test_auth.py ......                                           [ 23%]
tests/unit/test_camera_discovery.py ...............                      [ 32%]
tests/unit/test_cameras.py .......                                       [ 36%]
tests/unit/test_cli.py .......................................           [ 61%]
tests/unit/test_dates.py .........                                       [ 66%]
tests/unit/test_http_client.py ....                                      [ 69%]
tests/unit/test_models.py ..............                                 [ 78%]
tests/unit/test_recordings.py ..........                                 [ 84%]
tests/unit/test_ui.py .........................                          [100%]

================== 159 passed, 1 skipped in 72.32s ===================
```

### B. Strict Type Safety (`uv run mypy src tests`)
```
Success: no issues found in 41 source files
```

### C. Linting & Code Style (`uv run ruff check .`)
```
All checks passed!
```

---

## 3. Deviations & Edge Cases Handled

1. **Backwards Compatibility During Keychain Lookup**:
   - `keychain.py` attempts lookup against `username@host:port` first, then `username@host` (port 80 fallback), and finally legacy `host:port:username` format. This ensures seamless credential retention across upgrades.
2. **QByteArray Deserialization in QSettings**:
   - Explicitly handled type conversions when reading `QByteArray` / `bytes` / `str` types from `QSettings` across platforms.
3. **Double-hook on ComboBox Context Menus**:
   - Context menus were attached to both `QComboBox` and its embedded `QLineEdit` child editor to ensure right-clicking anywhere in the input fields triggers the `"Remove Stored Profile & Keychain Credentials"` action.
