# Implementation Plan - Task 006: NVR Auth, Two-Step ISAPI Dynamic Discovery with Cache & Concurrent Download Pool

## 1. Task Analysis & Requirements
Task 006 enhances `hikvision-downloader` with automated HTTP Digest/Basic authentication, two-step dynamic ISAPI camera discovery with lifecycle-aware caching, and a bounded thread-pool concurrency engine for multi-stream downloads with strict NVR protection limits.

### Key Deliverables:
1. **`.env.example` & Configuration Updates (`config.py`)**:
   - Provide clean placeholders for `HIKVISION_HOST`, `HIKVISION_PORT`, `HIKVISION_USERNAME`, `HIKVISION_PASSWORD`, and `HIKVISION_MAX_WORKERS` (default `2`).
   - Deprecate mandatory `HIKVISION_COOKIE` (mark as optional legacy fallback).
   - Update `config.py` to read port, username, password, and worker concurrency limits.
2. **`src/hikvision_downloader/core/auth.py`**:
   - Implement `create_authenticated_session(host, port, username, password, cookie=None, ...) -> requests.Session`.
   - Support `requests.auth.HTTPDigestAuth` with fallback to `HTTPBasicAuth` or cookie header.
   - Encapsulate parameters in `NVRAuthCredentials` with `SecretStr`.
   - Guarantee passwords are never logged, printed, or leaked in repr/error traces.
3. **`src/hikvision_downloader/core/cameras.py`**:
   - Implement two-step ISAPI camera discovery:
     - Query camera channels & labels from `/ISAPI/System/Video/inputs/channels`.
     - Query actual user tracks (101, 102, etc.) from `/ISAPI/ContentMgmt/record/tracks`.
   - Implement `CameraDiscoveryService`:
     - Maintain an in-memory profile cache for the active session.
     - Provide `get_cameras(...)`, `clear_cache()`, and `force_refresh` support.
     - Retain optional `config/cameras.toml` file loading purely as a local configuration override.
4. **`src/hikvision_downloader/core/downloads.py`**:
   - Implement `download_recordings_concurrent(...)` using `ThreadPoolExecutor`.
   - Enforce safety clamp: limit workers to a maximum of 4 (`1 <= workers <= 4`, default `2`) to prevent NVR hardware throttling.
   - Maintain thread-safe atomic `.part` management, progress aggregation, and cancellation token propagation.
5. **`src/hikvision_downloader/cli/app.py`**:
   - Add `--username` (`-u`), `--password` (`-p`), `--port`, and `--workers` (`-w`, default `2`, clamped max `4`) flags.
   - Prompt interactively for credentials (via `getpass` for password) if missing from `.env` and non-interactive is not set.
   - Wire dynamic camera discovery using `CameraDiscoveryService`.
   - Wire multi-worker download batch execution using `download_recordings_concurrent`.
6. **Tests**:
   - `tests/unit/test_auth.py`: Test digest/basic auth session creation, cookie fallback, and secret masking.
   - `tests/unit/test_camera_discovery.py`: Test two-step XML parsing (`inputs/channels` + `record/tracks`) and caching/invalidation logic.
   - `tests/functional/test_concurrent_downloads.py`: Test thread pool download execution, worker clamp, and atomic `.part` cleanup.

---

## 2. Target Files & Proposed Actions

| File | Operation | Description |
|---|---|---|
| `.gemini/logs/task-006-plan.md` | Create | This execution plan for Task 006. |
| `.env.example` | Create | Clean template with host, port, username, password, max workers, and optional cookie. |
| `.env.sample` | Modify | Update to match `.env.example` template conventions. |
| `src/hikvision_downloader/config.py` | Modify | Add NVR port, username, password, and worker concurrency limit configs. |
| `src/hikvision_downloader/core/auth.py` | Create | Session creation with Digest/Basic auth, SecretStr masking, and cookie fallback. |
| `src/hikvision_downloader/core/cameras.py` | Modify | Implement two-step ISAPI discovery parsing and `CameraDiscoveryService` with caching. |
| `src/hikvision_downloader/core/downloads.py` | Modify | Implement `download_recordings_concurrent` with bounded thread-pool and thread-safe progress. |
| `src/hikvision_downloader/core/__init__.py` | Modify | Export auth functions, discovery service, and concurrent downloader. |
| `src/hikvision_downloader/cli/app.py` | Modify | Add CLI flags (`--username`, `--password`, `--port`, `--workers`), interactive credential prompt, and discovery service integration. |
| `tests/unit/test_auth.py` | Create | Unit tests for auth session creation, SecretStr masking, and credentials validation. |
| `tests/unit/test_camera_discovery.py` | Create | Unit tests for two-step ISAPI XML parsing, camera model construction, and discovery service caching/invalidation. |
| `tests/functional/test_concurrent_downloads.py` | Create | Functional tests for multi-threaded downloads, worker clamping (1-4), atomic `.part` cleanup, and cancellation. |
| `.gemini/logs/task-006-walkthrough.md` | Create (Phase 2) | Implementation walkthrough capturing test results and verification outputs. |

---

## 3. Detailed Logic & Architecture Design

### 3.1 Authentication & Session Management (`src/hikvision_downloader/core/auth.py`)
- Function `create_authenticated_session`:
  ```python
  def create_authenticated_session(
      host: str | None = None,
      port: int = 80,
      username: str | None = None,
      password: str | SecretStr | None = None,
      cookie: str | None = None,
      user_agent: str | None = None,
      credentials: NVRAuthCredentials | None = None,
  ) -> requests.Session:
  ```
- **Priority & Auth Flow**:
  1. If `credentials` is provided or `username` and `password` are provided:
     - Unwrap `password` safely via `SecretStr.get_secret_value()`.
     - Configure `session.auth = requests.auth.HTTPDigestAuth(username, raw_password)`.
  2. Else if `cookie` is provided:
     - Set `session.headers["Cookie"] = cookie`.
  3. Else:
     - Raise `RuntimeError("No valid authentication credentials or session cookie provided.")`.
  4. Always set `session.headers["User-Agent"] = user_agent or USER_AGENT`.
- **Security Guarantee**:
  - `NVRAuthCredentials` stores passwords in `SecretStr`.
  - Passwords are never converted to string, printed, logged, or included in exception messages.

### 3.2 Two-Step Dynamic ISAPI Camera Discovery (`src/hikvision_downloader/core/cameras.py`)
- **Step 1: Parse Video Inputs Channels** (`/ISAPI/System/Video/inputs/channels`):
  - Parse `<VideoInputChannel>` elements.
  - Extract `<id>` (or `<inputPort>`), `<name>`, and IP address / video format if present.
- **Step 2: Parse Record Tracks** (`/ISAPI/ContentMgmt/record/tracks`):
  - Parse `<Track>` elements.
  - Extract `<id>` (e.g. 101, 102, 201, 202), `<inputPort>`, and track type/description (e.g. MainStream, SubStream).
  - Map tracks by input channel number: main stream (`*01`) and sub stream (`*02`).
- **Combine into Domain Models**:
  - Build `Camera(number=CameraNumber(ch_id), name=ch_name, ip_address=ch_ip or host, main_track=TrackId(main_id), sub_track=TrackId(sub_id))`.
- **`CameraDiscoveryService`**:
  - Maintains `_cache: dict[str, dict[CameraNumber, Camera]]`.
  - `get_cameras(session, host, port=80, config_file=None, force_refresh=False, timeout=120.0)`:
    - If `config_file` is specified and exists, load local TOML configuration override via `load_cameras(config_file)`.
    - If dynamic: check in-memory cache for key `f"{host}:{port}"`. If present and not `force_refresh`, return cached cameras.
    - Otherwise perform two-step ISAPI discovery, store in cache, and return cameras.
  - `clear_cache() -> None`: Clears in-memory cache.

### 3.3 Bounded Concurrent Download Pool (`src/hikvision_downloader/core/downloads.py`)
- Function `download_recordings_concurrent`:
  ```python
  def download_recordings_concurrent(
      session: requests.Session,
      host: str,
      recordings: Sequence[Recording],
      track_id: TrackId,
      output_dir: Path,
      start: int,
      count: int,
      max_workers: int = 2,
      timeout: float = 120.0,
      progress_callback: ProgressCallback | None = None,
      cancel_event: threading.Event | None = None,
  ) -> DownloadResult:
  ```
- **Concurrency & Safety Clamping**:
  - Enforce worker clamp: `effective_workers = max(1, min(max_workers, 4))`.
  - Slice recordings list according to `start` and `count` (with bounds validation).
  - Use `concurrent.futures.ThreadPoolExecutor(max_workers=effective_workers)`.
  - Protect aggregate state tracking with a `threading.Lock`:
    - `downloaded_files: int`
    - `skipped_files: int`
    - `downloaded_bytes: int`
    - `failed_index: int | None`
    - `error_message: str | None`
- **Cancellation & Cleanup**:
  - If `cancel_event` is set at any point, stop submitting new downloads and abort in-flight chunk streams.
  - `download_recording` safely unlinks `.part` files upon cancellation or failure.
  - Returns `DownloadResult` reflecting total files, skipped, downloaded, duration, and error status.

### 3.4 CLI Integration (`src/hikvision_downloader/cli/app.py`)
- Add CLI arguments:
  - `--username` / `-u`: NVR username.
  - `--password` / `-p`: NVR password.
  - `--port`: NVR port (default `80`).
  - `--workers` / `-w`: Number of concurrent workers (default `2`, max `4`).
  - `--refresh-cameras`: Force refresh camera discovery cache.
- Interactive authentication prompt:
  - If username/password and cookie are missing, and interactive mode is active:
    - Prompt for username (`input("NVR Username: ")`) and password (`getpass.getpass("NVR Password: ")`).
  - Create session via `create_authenticated_session(...)`.
- Dynamic camera discovery:
  - Instantiate `CameraDiscoveryService()`.
  - Load cameras dynamically using `service.get_cameras(session, effective_host, port=effective_port, config_file=CAMERA_CONFIG if CAMERA_CONFIG.exists() else None, force_refresh=args.refresh_cameras)`.
- Concurrent batch download:
  - Invoke `download_recordings_concurrent(...)` with configured worker count.

---

## 4. Verification and Testing Plan

### 4.1 Unit Tests (`tests/unit/test_auth.py`)
1. **Digest Authentication Session**:
   - Verify session created with `HTTPDigestAuth` when username and password are provided.
   - Verify `SecretStr` unwrapping and masking in representation.
2. **Cookie Fallback**:
   - Verify session created with `Cookie` header when cookie is provided without credentials.
3. **Credentials Validation**:
   - Verify `RuntimeError` raised when neither credentials nor cookie are provided.
   - Verify port bounds validation.

### 4.2 Unit Tests (`tests/unit/test_camera_discovery.py`)
1. **ISAPI XML Parsing**:
   - Parse sample `VideoInputChannelList` XML with multiple channels.
   - Parse sample `TrackList` XML with main (`101`, `201`) and sub (`102`, `202`) tracks.
   - Verify correct mapping into `Camera` domain entities.
2. **CameraDiscoveryService Caching & Invalidation**:
   - Test cache population on first query.
   - Test cache hit on subsequent query without HTTP calls.
   - Test `clear_cache()` and `force_refresh=True` triggers fresh network request.
3. **Local TOML Override**:
   - Verify local TOML configuration is loaded when config file exists and specified.

### 4.3 Functional Tests (`tests/functional/test_concurrent_downloads.py`)
1. **Concurrent Download Pool Execution**:
   - Download multiple files concurrently across worker threads.
   - Verify all destination files are created and atomic `.part` files are cleaned up.
2. **Worker Safety Clamp**:
   - Test passing `max_workers=10` clamps to 4 workers.
   - Test passing `max_workers=0` clamps to 1 worker.
3. **Concurrent Progress & Result Aggregation**:
   - Verify `DownloadProgress` events emitted safely from multiple threads.
   - Verify `DownloadResult` contains accurate `downloaded_bytes`, `downloaded_files`, and `skipped_files`.
4. **Cancellation in Thread Pool**:
   - Simulate `cancel_event.set()` during multi-worker download.
   - Verify in-flight downloads abort and `.part` files are unlinked.
5. **Mid-Batch Failure Handling**:
   - Simulate network failure in one worker thread.
   - Verify `DownloadResult(success=False, ...)` with proper failed index and error message.

### 4.4 Regression & Static Checks
- Run `uv run pytest` across all test suites (unit, functional, integration).
- Run `uv run mypy src tests` (100% strict type check with zero errors).
- Run `uv run ruff check .` (100% style/lint check with zero issues).

---

## 5. Invariant Checklist
- [x] Strict adherence to `.gemini/rules/1-workflow.md` (stopping at Step 5 for user approval).
- [x] Strict adherence to `.gemini/rules/2-security.md` (no hardcoded credentials, SecretStr masking, safe `.part` handling).
- [x] Strict adherence to `.gemini/rules/3-design.md` (core decoupled from CLI/UI, clean separation of concerns).
- [x] Strict adherence to `.gemini/rules/4-coding-standards.md` (100% strict type annotations, zero bare exceptions, max line length <= 150).
- [x] Strict adherence to `.gemini/rules/6-skills.md` (only permitted CLI commands used).
