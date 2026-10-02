# Task 006: NVR Auth, Two-Step ISAPI Dynamic Discovery with Cache & Concurrent Download Pool

## Objective
Implement automated HTTP Digest/Basic authentication, two-step dynamic ISAPI camera discovery with lifecycle-aware caching, and a bounded thread-pool concurrency engine for multi-stream downloads with strict NVR protection limits.

## Target Changes
1. **`.env.example`**:
   - Provide clean placeholders for `HIKVISION_HOST`, `HIKVISION_PORT`, `HIKVISION_USERNAME`, `HIKVISION_PASSWORD`, and `HIKVISION_MAX_WORKERS` (default `2`).
   - Deprecate mandatory `HIKVISION_COOKIE` (mark as optional legacy fallback).
2. **`src/hikvision_downloader/core/auth.py`**:
   - Implement `create_authenticated_session(host, port, username, password, cookie=None) -> requests.Session`.
   - Support `requests.auth.HTTPDigestAuth` with fallback to `HTTPBasicAuth` or cookie header.
   - Encapsulate parameters in `NVRAuthCredentials` with `SecretStr`.
3. **`src/hikvision_downloader/core/cameras.py`**:
   - Implement two-step ISAPI camera discovery:
     - Query camera channels & labels from `/ISAPI/System/Video/inputs/channels`.
     - Query actual user tracks (101, 102, etc.) from `/ISAPI/ContentMgmt/record/tracks`.
   - Implement `CameraDiscoveryService`:
     - Maintain an in-memory profile cache for the active session.
     - Provide `get_cameras(...)`, `clear_cache()`, and `force_refresh` support (CLI exits clear memory; UI can invoke `clear_cache()` on demand).
   - Retain optional `config/cameras.toml` file loading purely as a local configuration override.
4. **`src/hikvision_downloader/core/downloads.py`**:
   - Implement `download_recordings_concurrent(...)` using `ThreadPoolExecutor`.
   - Enforce safety clamp: limit workers to a maximum of 4 to prevent NVR hardware throttling.
   - Maintain thread-safe atomic `.part` management, progress aggregation, and cancellation token propagation.
5. **`src/hikvision_downloader/cli/app.py`**:
   - Add `--username`, `--password`, and `--workers` (`-w`, default `2`, max `4`) flags.
   - Prompt interactively for credentials if missing from `.env` and non-interactive is not set.
   - Wire dynamic camera discovery using `CameraDiscoveryService`.
6. **Tests**:
   - `tests/unit/test_auth.py`: Test digest/basic auth session creation and secret masking.
   - `tests/unit/test_camera_discovery.py`: Test two-step XML parsing (`inputs/channels` + `record/tracks`) and caching/invalidation logic.
   - `tests/functional/test_concurrent_downloads.py`: Test thread pool download execution, worker clamp, and atomic `.part` cleanup.

## Strict Invariants
- Adhere strictly to `.gemini/rules/1-workflow.md`, `2-security.md`, `3-design.md`, and `4-coding-standards.md`.
- 100% type annotations across all new code (zero bare `Any`).
- Passwords must NEVER be logged, printed, or included in error traces.
- Save Phase 1 plan to `.gemini/logs/task-006-plan.md` and stop for approval.
- Save Phase 2 walkthrough to `.gemini/logs/task-006-walkthrough.md`.