# Implementation Plan - Task 004: Comprehensive Multi-Tier Testing Suite & Offline Fixtures

## 1. Task Analysis & Objectives
The objective of Task 004 is to establish a clean, multi-tiered test architecture (`tests/unit/`, `tests/functional/`, `tests/integration/`, `tests/fixtures/`) with high test coverage across all `core/` modules, ensuring offline tests execute with zero live network dependency.

Key goals:
1. **Pyproject & Tooling Configuration**:
   - Add `pytest>=8.0` and `pytest-mock>=3.14` to dev dependency group in `pyproject.toml`.
   - Configure `[tool.pytest.ini_options]` with `testpaths = ["tests"]`, `markers = ["integration: marks tests requiring live NVR hardware"]`, and warning filters.
2. **Offline Synthetic Fixtures (`tests/fixtures/`)**:
   - `daily_distribution.xml`: ISAPI daily distribution XML representing recorded and non-recorded days.
   - `cm_search_result.xml`: CMSearch XML response containing multiple `searchMatchItem` entries with RTSP playback URIs and parameters.
   - `cm_search_empty.xml`: Empty search result response.
3. **Unit Test Suite (`tests/unit/`)**:
   - `test_models.py`: Comprehensive validation for `Camera`, `RecordingDate`, `Recording`, `DownloadProgress`, `DownloadResult`, `NVRAuthCredentials`, `NVRConnectionProfile`, `StreamType`, `StreamQuality`, `TrackId`, `CameraNumber`, `ByteCount`, `MegabitsPerSecond`, `ISODatetimeStr`.
   - `test_dates.py`: Validate `build_daily_distribution_xml`, `parse_daily_distribution`, `previous_month`, `search_month` (mocked HTTP), and `discover_available_dates` (mocked HTTP).
   - `test_cameras.py`: Validate `load_cameras` with valid TOML, missing configuration files, duplicate camera numbers, duplicate track IDs, missing keys, and malformed structures.
   - `test_recordings.py`: Validate `build_search_xml`, `get_query_value`, `parse_search_response`, `search_recordings` (mocked HTTP), `get_all_recordings` (mocked pagination), `recording_total_size`, and `save_recording_list`.
4. **Functional Test Suite (`tests/functional/`)**:
   - `test_download_engine.py`: Mocked HTTP chunk streaming, `.part` temporary file lifecycle, atomic rename to target `.mp4`, skipping pre-existing files, zero-byte error handling, network error recovery, and batch `download_recordings` aggregation.
   - `test_cancellation.py`: Verify immediate abort and atomic `.part` file deletion upon `threading.Event` triggering before download, during chunk streaming, and between batch items.
5. **Integration Test Suite (`tests/integration/`)**:
   - `test_live_nvr.py`: Hardware integration tests tagged with `@pytest.mark.integration`, auto-skipped when `.env` is absent or live environment variables are unconfigured.
6. **Strict Invariants**:
   - Adhere strictly to `.gemini/rules/1-workflow.md` and `.gemini/rules/4-coding-standards.md`.
   - 100% strict type annotations on all test functions and fixtures (zero bare `Any`).
   - Pure offline execution for `tests/unit/` and `tests/functional/`.
   - Clean up old flat test files in `tests/` (`tests/test_*.py`).

---

## 2. Target Files & Proposed Actions

| File | Operation | Description |
|---|---|---|
| `.gemini/logs/task-004-plan.md` | Create | This execution plan for Task 004. |
| `pyproject.toml` | Modify | Add `pytest-mock>=3.14.0` to dev dependencies; configure `[tool.pytest.ini_options]` with test paths and `integration` marker. |
| `tests/fixtures/daily_distribution.xml` | Create | Synthetic ISAPI daily distribution XML fixture. |
| `tests/fixtures/cm_search_result.xml` | Create | Synthetic ISAPI CMSearch match items fixture. |
| `tests/fixtures/cm_search_empty.xml` | Create | Synthetic ISAPI CMSearch empty result fixture. |
| `tests/unit/test_models.py` | Create | Unit tests for domain models, validation constraints, and semantic types. |
| `tests/unit/test_dates.py` | Create | Unit tests for date XML generation, parsing, month navigation, and discovery logic. |
| `tests/unit/test_cameras.py` | Create | Unit tests for camera TOML loading, duplicate detection, and schema validation. |
| `tests/unit/test_recordings.py` | Create | Unit tests for search XML generation, query parsing, pagination, and CSV export. |
| `tests/functional/test_download_engine.py` | Create | Functional tests for chunk streaming, atomic rename, skip caching, and batch execution. |
| `tests/functional/test_cancellation.py` | Create | Functional tests for cancellation token handling and `.part` file cleanup. |
| `tests/integration/test_live_nvr.py` | Create | Integration tests for live NVR connection and queries (auto-skipped if offline). |
| `tests/test_models.py` | Delete | Legacy flat test file replaced by `tests/unit/test_models.py`. |
| `tests/test_dates.py` | Delete | Legacy flat test file replaced by `tests/unit/test_dates.py`. |
| `tests/test_cameras.py` | Delete | Legacy flat test file replaced by `tests/unit/test_cameras.py`. |
| `tests/test_recordings.py` | Delete | Legacy flat test file replaced by `tests/unit/test_recordings.py`. |
| `tests/test_downloads.py` | Delete | Legacy flat test file replaced by `tests/functional/`. |
| `.gemini/logs/task-004-walkthrough.md` | Create (Phase 2) | Implementation walkthrough capturing test results and verification logs. |

---

## 3. Detailed Logic & Test Design

### 3.1 `pyproject.toml` Updates
- Dev dependencies:
  ```toml
  [dependency-groups]
  dev = [
      "mypy>=1.15.0",
      "pytest>=8.0.0",
      "pytest-mock>=3.14.0",
      "ruff>=0.16.10",
      "types-requests>=2.32.0",
  ]
  ```
- Pytest configuration:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  markers = [
      "integration: marks tests as integration tests that require live NVR hardware (deselect with '-m \"not integration\"')",
  ]
  filterwarnings = [
      "error",
      "ignore::DeprecationWarning",
  ]
  ```

### 3.2 Fixture Files (`tests/fixtures/`)
- `daily_distribution.xml`: Valid Hikvision XML containing multiple `<day>` nodes with `<dayOfMonth>` and `<record>true|false</record>`.
- `cm_search_result.xml`: Valid Hikvision XML containing `<searchMatchItem>` nodes with ISO start/end times and RTSP `playbackURI` containing file metadata.
- `cm_search_empty.xml`: Empty search response with `numOfMatches = 0`.

### 3.3 Unit Tests (`tests/unit/`)
1. **`test_models.py`**:
   - `test_camera_valid`: Property verification (`display_name`, `archive_name`, `stream_quality`, `stream_name`, `track_id`).
   - `test_camera_validation_failures`: Rejection of `number < 1`, empty name, empty ip_address, `main_track < 1`, `sub_track < 1`.
   - `test_recording_date_valid`: Value date object, iso string.
   - `test_recording_date_invalid`: Invalid day for month (e.g. Feb 30), year < 2000, year > 2100, month < 1 or > 12.
   - `test_recording_valid`: Size conversion (`size_mb`), alias `size`.
   - `test_recording_invalid`: Negative `size_bytes`, empty fields.
   - `test_nvr_auth_credentials`: SecretStr masking on password, port boundaries.
   - `test_nvr_connection_profile`: Default service name, validation.
   - `test_download_progress`: Validation on negative values for bytes/speed/elapsed.
   - `test_download_result`: Validation on negative bytes, failed index mapping.

2. **`test_dates.py`**:
   - `test_build_daily_distribution_xml_valid`: Checks XML tag structure for year/month.
   - `test_build_daily_distribution_xml_invalid`: Out of range year/month errors.
   - `test_parse_daily_distribution_from_fixture`: Load `tests/fixtures/daily_distribution.xml` and verify parsed list of `RecordingDate`.
   - `test_parse_daily_distribution_empty_and_corrupt`: Empty string and invalid XML node handling.
   - `test_previous_month`: Boundary at January (roll to previous year 12) and normal months.
   - `test_search_month_mocked`: Mock HTTP POST, verify URL format, payload, and returned dates.
   - `test_search_month_invalid_track`: Raise ValueError for track < 1.
   - `test_discover_available_dates_two_months`: Mock current/previous month with no recordings in previous month.
   - `test_discover_available_dates_three_months`: Mock recordings found in previous month, triggering search of older month.

3. **`test_cameras.py`**:
   - `test_load_cameras_valid`: Parse valid TOML config with multiple cameras.
   - `test_load_cameras_missing_file`: Verify `FileNotFoundError`.
   - `test_load_cameras_duplicate_number`: Raise `ValueError` on duplicate camera numbers.
   - `test_load_cameras_duplicate_main_track`: Raise `ValueError` on duplicate main track IDs across cameras.
   - `test_load_cameras_duplicate_sub_track`: Raise `ValueError` on duplicate sub track IDs.
   - `test_load_cameras_invalid_structure`: Raise `ValueError` when `cameras` table is missing or empty.

4. **`test_recordings.py`**:
   - `test_build_search_xml_valid`: Validate search ID, track ID, time span, position, batch size.
   - `test_build_search_xml_invalid`: Reject track < 1, position < 0, batch_size < 1.
   - `test_get_query_value`: Query extraction and missing key handling.
   - `test_parse_search_response_from_fixture`: Load `tests/fixtures/cm_search_result.xml` and verify parsed `Recording` objects.
   - `test_parse_search_response_empty_fixture`: Load `tests/fixtures/cm_search_empty.xml` and verify empty list.
   - `test_search_recordings_mocked`: Verify request headers, URL, payload.
   - `test_get_all_recordings_pagination`: Verify multi-batch loop that aggregates recordings until batch size is less than max.
   - `test_recording_total_size`: Aggregation sum.
   - `test_save_recording_list`: CSV formatting, column order, directory creation.

### 3.4 Functional Tests (`tests/functional/`)
1. **`test_download_engine.py`**:
   - `test_format_duration`: Formats seconds, minutes, hours correctly.
   - `test_build_download_url`: Correct ISAPI download URL construction with formatted datetime.
   - `test_download_recording_chunk_streaming`: Mock `request_with_retry` streaming bytes; verify temporary `.part` file written and atomically renamed to destination `.mp4`.
   - `test_download_recording_skip_existing`: Existing file with size > 0 is skipped; progress callback receives `is_skipped=True`.
   - `test_download_recording_zero_byte_error`: Response with zero bytes causes `.part` cleanup and returns failure.
   - `test_download_recording_network_error`: RequestException triggers cleanup of `.part` and returns failure.
   - `test_download_recordings_batch_success`: Full slice download aggregating counts and byte metrics.
   - `test_download_recordings_batch_bounds_error`: Reject invalid start or count ranges.
   - `test_download_recordings_batch_midway_failure`: Stop batch on single file failure and populate `failed_index`.

2. **`test_cancellation.py`**:
   - `test_download_recording_cancelled_before_start`: `cancel_event.set()` before download returns immediately without network calls.
   - `test_download_recording_cancelled_during_streaming`: Cancel event set during chunk iteration aborts loop, unlinks `.part` file, and returns cancellation error.
   - `test_download_recordings_batch_cancelled`: Batch aborts before next file, cleans up, and returns `DownloadResult(success=False, error_message="Batch download cancelled by user")`.

### 3.5 Integration Tests (`tests/integration/`)
1. **`test_live_nvr.py`**:
   - Tagged with `@pytest.mark.integration`.
   - Auto-checks for `.env` credentials (`NVR_HOST`, `NVR_USERNAME`, `NVR_PASSWORD`).
   - If unconfigured or NVR unreachable, calls `pytest.skip("Live NVR credentials not configured or unreachable")`.
   - When configured, tests live session authentication and track discovery.

---

## 4. Verification Plan

### Automated Checks
1. **Dependency Installation**:
   - `uv sync --group dev`
2. **Offline Test Suite Execution**:
   - `uv run pytest tests/unit tests/functional -v` (Must pass 100% offline).
3. **Integration Test Suite Filter**:
   - `uv run pytest -m "not integration"` (All unit and functional tests pass, integration tests skipped/excluded).
   - `uv run pytest tests/integration -v` (Skips gracefully if hardware is offline).
4. **Static Type Checking**:
   - `uv run mypy src tests` (100% strict type compliance, zero errors).
5. **Code Formatting & Linting**:
   - `uv run ruff check src tests`
   - `uv run ruff format --check src tests`
