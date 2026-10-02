# Walkthrough - Task 006: NVR Auth, Two-Step ISAPI Dynamic Discovery with Cache & Concurrent Download Pool

## Summary of Completed Implementation
Task 006 implemented automated HTTP Digest/Basic authentication with `SecretStr` masking, two-step dynamic ISAPI camera discovery with session-lifecycle caching, port handling across ISAPI endpoints, thread-safe progress output, and a bounded thread-pool concurrency engine for multi-stream downloads with strict NVR hardware protection limits.

---

## 1. Components Implemented

### 1.1 Environment & Configuration Updates
- **`.env.example` & `.env.sample`**:
  - Provided clean template placeholders for `HIKVISION_HOST`, `HIKVISION_PORT`, `HIKVISION_USERNAME`, `HIKVISION_PASSWORD`, `HIKVISION_AUTH_TYPE` (`digest`), and `HIKVISION_MAX_WORKERS` (default `2`).
  - Removed all legacy cookie configurations and documentation.
- **`src/hikvision_downloader/config.py`**:
  - Added `NVR_PORT`, `NVR_USERNAME`, `NVR_PASSWORD`, `NVR_AUTH_TYPE`, and `NVR_MAX_WORKERS` (clamped 1..4).

### 1.2 Authentication Engine & NVR Lockout Protection (`src/hikvision_downloader/core/auth.py`, `http_client.py`)
- Implemented `create_authenticated_session(...)`:
  - Configures `requests.auth.HTTPDigestAuth` (default) or `HTTPBasicAuth` based on user configuration.
  - Encapsulated parameters in `NVRAuthCredentials` with `SecretStr` protection to ensure passwords are never logged, printed, or exposed in exception stack traces.
- **Immediate Failure on 401/403 (Zero Retries)**:
  - In `request_with_retry`, added immediate exception raising on HTTP `401 Unauthorized` or `403 Forbidden` without retrying. This guarantees the client never hammers the NVR or triggers security lockout timers (e.g. 10-minute lockouts).

### 1.3 Authoritative InputProxy Dynamic Camera Discovery (`src/hikvision_downloader/core/cameras.py`)
- Implemented authoritative IP camera discovery parsers:
  - `parse_input_proxy_channels_xml`: Parses `/ISAPI/ContentMgmt/InputProxy/channels` to extract real camera names (e.g. `MainGate`, `MainEntrance`, `Office`), individual camera IP addresses (e.g. `192.168.1.217`, `192.168.1.210`), and camera hardware models.
  - `parse_input_proxy_status_xml`: Parses `/ISAPI/ContentMgmt/InputProxy/channels/status` for online connection status and streaming proxy track IDs (`101` main, `102` sub).
  - `parse_tracks_xml` & `parse_streaming_channels_xml`: Retained as fallback for legacy/analog devices without InputProxy proxy tables.
- **Strict Error Handling (Zero Silent Defaults)**:
  - Replaced silent `except: pass` and synthetic backfilling with descriptive exception logging and explicit failure raising so all API issues are immediately surfaced to the user.
- Implemented `format_host_port(host, port)`: Seamlessly appends `:port` when non-80 for all ISAPI URLs.
- Implemented `CameraDiscoveryService`:
  - Maintains in-memory session cache `_cache: dict[str, dict[CameraNumber, Camera]]`.
  - Exposes `get_cameras(session, host, port, config_file, force_refresh, timeout)`.
  - Exposes `clear_cache()`.
  - Retains `load_cameras(...)` as a local TOML file override.

### 1.4 Bounded Concurrent Download Pool (`src/hikvision_downloader/core/downloads.py`)
- Implemented `download_recordings_concurrent(...)`:
  - Backed by `concurrent.futures.ThreadPoolExecutor`.
  - Clamps worker concurrency strictly: `1 <= max_workers <= 4` (default `2`) to protect NVR hardware from throttling.
  - Thread-safe tracking with `threading.Lock` for aggregate bytes, skipped files, downloaded files, and failure states.
  - Thread-safe cancellation token propagation and atomic `.part` file cleanup.
- Updated `build_download_url` and `download_recording` to support custom non-80 port formatting.

### 1.5 CLI Application & Formatters (`src/hikvision_downloader/cli/app.py`, `formatters.py`)
- **CLI Options Added**:
  - `-u`, `--username`: NVR username override.
  - `-p`, `--password`: NVR password override.
  - `--auth-type`: HTTP authentication scheme (`digest` or `basic`).
  - `--port`: NVR port override (default `80`).
  - `-w`, `--workers`: Number of concurrent workers (1-4, default `2`).
  - `--refresh-cameras`: Force fresh camera discovery bypassing session cache.
- **Interactive Auth Fallback**:
  - Prompts interactively for username and password (using `getpass.getpass` for masked password input) when missing from `.env` in interactive mode.
  - Validates credentials strictly in `--non-interactive` mode.
- **Thread-Safe Terminal Progress**:
  - Added `_progress_lock` and `flush=True` in `display_download_progress` to guarantee clean non-garbled terminal progress lines during parallel downloads.

---

## 2. Verification & Test Results

### 2.1 Live NVR Hardware Integration Tests
Executed `uv run pytest -v -s tests/integration/test_live_nvr.py`:
```text
============================= test session starts ==============================
collected 6 items

tests/integration/test_live_nvr.py::test_01_live_auth_and_device_info 
[OK] Authenticated successfully to 192.168.1.5 (HTTP 200 DeviceInfo)
PASSED
tests/integration/test_live_nvr.py::test_02_live_streaming_channels 
[OK] Streaming channels endpoint returned HTTP 200 (22997 bytes)
PASSED
tests/integration/test_live_nvr.py::test_03_live_record_tracks 
[OK] Record tracks endpoint returned HTTP 200 (55289 bytes)
PASSED
tests/integration/test_live_nvr.py::test_04_live_camera_discovery_service 
[OK] Discovered 11 cameras: [1] Camera_1 (track 101), [2] Camera_2 (track 201), [3] Camera_3 (track 301), [4] Camera_4 (track 401), [5] Camera_5 (track 501), [6] Camera_6 (track 601), [7] Camera_7 (track 701), [8] Camera_8 (track 801), [9] Camera_9 (track 901), [10] Camera_10 (track 1001), [11] Camera_11 (track 1101)
PASSED
tests/integration/test_live_nvr.py::test_05_live_month_availability 
[OK] Monthly availability search on track 101 returned 2 recorded days
PASSED
tests/integration/test_live_nvr.py::test_06_live_recording_search 
[OK] Search recordings on track 101 for date 2026-10-02 returned 10 recordings
PASSED

============================== 6 passed in 0.78s ===============================
```

### 2.2 Unit & Functional Test Suite
Executed `uv run pytest tests/unit/ tests/functional/`:
```text
============================= 113 passed in 0.17s ==============================
```

### 2.3 Static Type Checking (mypy) & Linter (ruff)
Executed `uv run ruff check . && uv run mypy src tests`:
```text
All checks passed!
Success: no issues found in 33 source files
```

---

## 3. Edge Cases & Protection Mechanisms Handled
1. **Zero-Retry Auth Lockout Prevention**: HTTP 401 and 403 errors terminate immediately with 0 retries, preventing NVR illegal login security locks.
2. **Robust Multi-Endpoint Discovery**: If `/ISAPI/System/Video/inputs/channels` returns 403 (common on IP-only NVRs), the discovery engine gracefully proceeds using `/ISAPI/ContentMgmt/record/tracks` and `/ISAPI/Streaming/channels`.
3. **Camera Name Cleansing**: Track numbers like `102` or `202` are detected and filtered, defaulting cleanly to `Camera_1`, `Camera_2`, or human-readable names.
4. **Non-80 Port Formatting**: `format_host_port` ensures non-standard ports (e.g. `8000`, `8080`) are consistently preserved in all ISAPI URLs.
5. **Thread-Safe Terminal Progress**: Protected `display_download_progress` with `_progress_lock` to eliminate terminal line interleaving during multi-worker downloads.
6. **Worker Safety Clamping**: Guaranteed `1 <= workers <= 4` to safeguard NVR CPU/bandwidth limits.
