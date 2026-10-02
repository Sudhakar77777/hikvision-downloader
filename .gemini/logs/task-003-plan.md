# Implementation Plan - Task 003: Core Decoupling, Pydantic Domain Models & Strict Type Annotations

## 1. Task Analysis & Objectives
The goal of Task 003 is to modernize the Hikvision Downloader codebase to Python >=3.14.7 standards, introduce Pydantic v2 domain models with strict validation constraints and semantic types, decouple all business logic from presentation/CLI concerns, and enforce 100% complete type annotations across all modules in `src/`:
- Update `pyproject.toml` to require Python `>=3.14.7` (matching `.python-version` `3.14.7`) and add `pydantic>=2.0`.
- Restructure `src/hikvision_downloader/core/` to contain pure business logic with zero terminal I/O (`print()`, `input()`, ANSI formatting):
  - `models.py`: Semantic `NewType` primitives, `StrEnum` types, and validated immutable Pydantic domain models (`Camera`, `RecordingDate`, `Recording`, `DownloadProgress`, `DownloadResult`, `NVRAuthCredentials`, `NVRConnectionProfile`).
  - `dates.py`: Pure ISAPI date discovery queries, XML parsing, month generation, and response validation.
  - `cameras.py`: Pure TOML camera configuration loading, dictionary validation, duplicate detection, and camera mapping.
  - `recordings.py`: Pure CMSearch XML generation, XML response parsing, pagination validation, total size computation, and CSV export.
  - `downloads.py`: Pure streaming HTTP download, atomic `.part` staging, `threading.Event` cancellation, byte size verification, and typed progress callback protocol.
- Restructure `src/hikvision_downloader/cli/` to encapsulate all terminal presentation:
  - `interactive.py`: User prompts, interactive selections, ISO date format validation, bounds validation, and confirmation handlers.
  - `formatters.py`: Header rendering, tabular formatting, date availability matrices, recording tables, and progress display.
- Refactor `src/hikvision_downloader/downloader.py` into a thin CLI orchestrator coordinating session creation, presentation, and core business logic.
- Type annotate `src/hikvision_downloader/http_client.py` and `src/hikvision_downloader/config.py` with 100% complete type signatures.

---

## 2. Target Files & Proposed Actions

| File | Operation | Description |
|---|---|---|
| `.gemini/logs/task-003-plan.md` | Update | This execution plan for Task 003 with Python >=3.14.7 specification and comprehensive validation specifications. |
| `pyproject.toml` | Modify | Update `requires-python = ">=3.14.7"`, add `pydantic>=2.0`, and add `mypy` / `types-requests` to dev dependencies. |
| `src/hikvision_downloader/core/__init__.py` | Create | Package initialization exporting core services and models. |
| `src/hikvision_downloader/core/models.py` | Create | Pydantic domain models with strict field validation, `StrEnum`s, and `NewType` semantic primitives (`TrackId`, `CameraNumber`, `ByteCount`, `MegabitsPerSecond`, `ISODatetimeStr`, `NVRHost`). |
| `src/hikvision_downloader/core/dates.py` | Create | Pure ISAPI date distribution search, XML parsing, and input validation with zero `print()` / `input()`. |
| `src/hikvision_downloader/core/cameras.py` | Create | Pure TOML camera config parser with schema validation and duplicate checking; zero `print()` / `input()`. |
| `src/hikvision_downloader/core/recordings.py` | Create | Pure CMSearch XML payload builder, parser, pagination bounds checking, total size calculator, and CSV exporter. |
| `src/hikvision_downloader/core/downloads.py` | Create | Pure streaming downloader with atomic `.part` management, byte-count verification, typed `ProgressCallback`, and `threading.Event` cancellation token. |
| `src/hikvision_downloader/cli/__init__.py` | Create | Package initialization exporting CLI handlers. |
| `src/hikvision_downloader/cli/formatters.py` | Create | Terminal rendering functions (header, camera table, dates matrix, recording list, progress callback display, download summary). |
| `src/hikvision_downloader/cli/interactive.py` | Create | Interactive user input prompts with input parsing and bounds validation (`ask_recording_date`, `ask_camera`, `ask_stream`, `ask_download_selection`, `confirm_download`). |
| `src/hikvision_downloader/downloader.py` | Modify | Thin orchestrator wiring together `config`, `http_client`, `core.*`, and `cli.*`. |
| `src/hikvision_downloader/http_client.py` | Modify | Add strict type annotations and credential validation to `make_session` and `request_with_retry`. |
| `src/hikvision_downloader/config.py` | Modify | Add explicit type annotations and environment variable validation to config variables. |
| `src/hikvision_downloader/cameras.py` | Delete | Replaced by `core/cameras.py` and `cli/`. |
| `src/hikvision_downloader/dates.py` | Delete | Replaced by `core/dates.py` and `cli/`. |
| `src/hikvision_downloader/recordings.py` | Delete | Replaced by `core/recordings.py` and `cli/`. |
| `src/hikvision_downloader/downloads.py` | Delete | Replaced by `core/downloads.py` and `cli/`. |
| `.gemini/logs/task-003-walkthrough.md` | Create (Phase 2) | Walkthrough document capturing implementation details, verification results, and diffs. |

---

## 3. Detailed Logic, Validations & Architecture Design

### 3.1 Domain Models & Validations (`src/hikvision_downloader/core/models.py`)
- **Semantic Primitives:**
  ```python
  from enum import StrEnum
  from typing import Callable, NewType
  from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

  TrackId = NewType("TrackId", int)
  CameraNumber = NewType("CameraNumber", int)
  ByteCount = NewType("ByteCount", int)
  MegabitsPerSecond = NewType("MegabitsPerSecond", float)
  ISODatetimeStr = NewType("ISODatetimeStr", str)
  NVRHost = NewType("NVRHost", str)
  ```
- **Enums:**
  - `StreamType(StrEnum)`: `MAIN = "main"`, `SUB = "sub"`
  - `StreamQuality(StrEnum)`: `HD = "HD"`, `SD = "SD"`
- **Entities & Data Objects (Frozen Pydantic Models with Strict Validations):**
  - `Camera`:
    - `number: CameraNumber = Field(..., gt=0, description="Camera channel number (>=1)")`
    - `name: str = Field(..., min_length=1, description="Camera display name")`
    - `ip_address: str = Field(..., min_length=1, description="Camera IP address or hostname")`
    - `main_track: TrackId = Field(..., gt=0, description="Main stream ISAPI track ID")`
    - `sub_track: TrackId = Field(..., gt=0, description="Sub stream ISAPI track ID")`
    - Helper properties: `display_name -> str`, `archive_name -> str`.
    - Helper methods: `stream_quality(stream: StreamType) -> StreamQuality`, `stream_name(stream: StreamType) -> str`, `track_id(stream: StreamType) -> TrackId`.
  - `RecordingDate`:
    - `year: int = Field(..., ge=2000, le=2100)`
    - `month: int = Field(..., ge=1, le=12)`
    - `day: int = Field(..., ge=1, le=31)`
    - Validator: Validates `date(year, month, day)` construction to reject invalid dates like Feb 31.
    - Helper properties: `value -> date`, `iso -> ISODatetimeStr`.
  - `Recording`:
    - `start: ISODatetimeStr = Field(..., min_length=1)`
    - `end: ISODatetimeStr = Field(..., min_length=1)`
    - `name: str = Field(..., min_length=1)`
    - `size_bytes: ByteCount = Field(..., ge=0)`
    - `playback_uri: str = Field(..., min_length=1)`
    - Helper properties: `size_mb -> float`, `size -> ByteCount`.
  - `NVRAuthCredentials`:
    - `host: str = Field(..., min_length=1)`
    - `username: str = Field(..., min_length=1)`
    - `password: SecretStr`
    - `port: int = Field(default=80, ge=1, le=65535)`
  - `NVRConnectionProfile`:
    - `name: str = Field(..., min_length=1)`
    - `host: str = Field(..., min_length=1)`
    - `username: str = Field(..., min_length=1)`
    - `keyring_service: str = "hikvision_downloader"`
  - `DownloadProgress`:
    - `current_index: int = Field(..., ge=1)`
    - `total_files: int = Field(..., ge=1)`
    - `filename: str = Field(..., min_length=1)`
    - `bytes_downloaded: ByteCount = Field(..., ge=0)`
    - `file_size_bytes: ByteCount = Field(..., ge=0)`
    - `speed_mbps: MegabitsPerSecond = Field(..., ge=0.0)`
    - `elapsed_seconds: float = Field(..., ge=0.0)`
    - `is_skipped: bool = False`
  - `DownloadResult`:
    - `success: bool`
    - `total_files: int = Field(..., ge=0)`
    - `downloaded_files: int = Field(..., ge=0)`
    - `skipped_files: int = Field(..., ge=0)`
    - `downloaded_bytes: ByteCount = Field(..., ge=0)`
    - `total_duration_seconds: float = Field(..., ge=0.0)`
    - `failed_index: int | None = None`
    - `error_message: str | None = None`
  - `ProgressCallback = Callable[[DownloadProgress], None]`

### 3.2 Core Modules & Business Logic Validations (`src/hikvision_downloader/core/`)
- **`dates.py`**:
  - `build_daily_distribution_xml(year: int, month: int) -> str`: Validates `2000 <= year <= 2100` and `1 <= month <= 12`.
  - `parse_daily_distribution(xml_text: str, year: int, month: int) -> list[RecordingDate]`: Parses XML using `ElementTree`, handles malformed nodes safely, filters out non-recording days, returns sorted validated `RecordingDate` list.
  - `search_month(session: requests.Session, host: str, track_id: TrackId, year: int, month: int, timeout: float = 120.0) -> list[RecordingDate]`: Validates `track_id > 0`, executes POST with retry, parses response.
  - `previous_month(year: int, month: int) -> tuple[int, int]`: Returns previous calendar year and month.
  - `discover_available_dates(session: requests.Session, host: str, discovery_track_id: TrackId, today: date | None = None, timeout: float = 120.0) -> tuple[dict[tuple[int, int], list[RecordingDate]], float]`: Discovers available dates across current, previous, and optionally older months.
- **`cameras.py`**:
  - `load_cameras(config_file: str | Path) -> dict[CameraNumber, Camera]`: Validates file existence, non-empty TOML structure, parses each camera item into a validated `Camera` model, verifies no duplicate camera numbers or track IDs, returns `dict[CameraNumber, Camera]`.
- **`recordings.py`**:
  - `build_search_xml(track_id: TrackId, start_time: str, end_time: str, position: int, batch_size: int = 1) -> str`: Validates `position >= 0`, `batch_size >= 1`.
  - `get_query_value(url: str, key: str) -> str | None`: Parses URL query string safely.
  - `parse_search_response(xml_text: str) -> list[Recording]`: Extracts and validates `searchMatchItem` tags, parses `name`, `size`, `start`, `end`, and `playback_uri`.
  - `search_recordings(session: requests.Session, host: str, track_id: TrackId, recording_date: date, position: int, batch_size: int = 1, timeout: float = 120.0) -> list[Recording]`: Retrieves one batch of recordings.
  - `get_all_recordings(session: requests.Session, host: str, track_id: TrackId, recording_date: date, batch_size: int = 1, timeout: float = 120.0) -> list[Recording]`: Paginates until complete.
  - `recording_total_size(recordings: Sequence[Recording]) -> ByteCount`: Calculates sum of recording sizes in bytes.
  - `save_recording_list(recordings: Sequence[Recording], output_dir: Path, camera_number: CameraNumber, camera_name: str, stream_name: str, recording_date: date) -> Path`: Creates directory if needed, writes CSV with header and records, returns written `Path`.
- **`downloads.py`**:
  - `format_duration(seconds: float) -> str`: Formats duration string.
  - `build_download_url(host: str, recording: Recording, track_id: TrackId) -> str`: Builds ISAPI download URL with URL-encoded query parameters.
  - `download_recording(session: requests.Session, host: str, recording: Recording, track_id: TrackId, destination: Path, current_index: int, total_files: int, timeout: float = 120.0, progress_callback: ProgressCallback | None = None, cancel_event: threading.Event | None = None) -> tuple[bool, float, ByteCount, bool, str | None]`:
    - Checks `cancel_event` before starting.
    - Validates `recording.name` is present.
    - Checks if `destination` already exists with size > 0 (skips download).
    - Creates parent directories safely.
    - Streams chunks to atomic `.part` file, emitting `DownloadProgress` events.
    - Checks `cancel_event` between chunks; if cancelled, cleans up `.part` file.
    - Validates downloaded `.part` file has `st_size > 0` before renaming to `destination`.
    - Handles exceptions with automatic cleanup of partial `.part` files.
  - `download_recordings(session: requests.Session, host: str, recordings: Sequence[Recording], track_id: TrackId, output_dir: Path, start: int, count: int, timeout: float = 120.0, progress_callback: ProgressCallback | None = None, cancel_event: threading.Event | None = None) -> DownloadResult`:
    - Validates selection bounds: `1 <= start <= len(recordings)` and `count >= 1` and `start + count - 1 <= len(recordings)`.
    - Iterates over selected recordings, emitting progress, checking cancellation, and collecting aggregate `DownloadResult`.

### 3.3 CLI Modules & Input Validations (`src/hikvision_downloader/cli/`)
- **`formatters.py`**:
  - `display_header(host: str) -> None`
  - `display_available_dates(months: dict[tuple[int, int], list[RecordingDate]]) -> None`
  - `display_camera_list(cameras: dict[CameraNumber, Camera]) -> None`
  - `display_selection(camera: Camera, stream: StreamType) -> None`
  - `display_recording_list(recordings: Sequence[Recording]) -> None`
  - `display_download_progress(progress: DownloadProgress) -> None`: Formats progress line (`[current/total] filename size_mb duration status`).
  - `display_download_summary(camera: Camera, stream: StreamType, recording_date: date, track_id: TrackId, selection: tuple[int, int], search_duration: float, result: DownloadResult) -> None`
- **`interactive.py`**:
  - `ask_recording_date(months: dict[tuple[int, int], list[RecordingDate]]) -> date | None`: Validates ISO date format (`YYYY-MM-DD`), ensures input is within discovered available dates, handles 'q' to quit.
  - `ask_camera(cameras: dict[CameraNumber, Camera]) -> Camera | None`: Validates integer input, verifies camera number exists in `cameras` map, handles 'q' to quit.
  - `ask_stream() -> StreamType | None`: Validates choice is '1' (main) or '2' (sub), handles 'q' to quit.
  - `ask_download_selection(total: int) -> tuple[int, int] | None`: Validates Y/n input for full batch, or parses "START COUNT", validating `start >= 1`, `count >= 1`, `start + count - 1 <= total`.
  - `confirm_download(camera: Camera, stream: StreamType, recording_date: date, recordings: Sequence[Recording], start: int, count: int) -> bool`: Prompts confirmation with selected file count and reported size.

### 3.4 Orchestrator (`src/hikvision_downloader/downloader.py`)
- Coordinates the CLI workflow:
  1. Header display
  2. Camera config loading & validation
  3. HTTP session creation
  4. Date discovery & interactive selection
  5. Camera & stream selection
  6. Recording search & metadata extraction
  7. Recording list CSV export & table display
  8. Interactive range selection & confirmation
  9. Core download execution with callback-driven CLI progress formatting
  10. Final summary statistics display

### 3.5 Infrastructure & HTTP Client (`http_client.py` & `config.py`)
- `http_client.py`: Strict type annotations for `make_session(cookie: str | None = None, user_agent: str = USER_AGENT) -> requests.Session` and `request_with_retry(...) -> requests.Response`. Validates authentication cookies, status codes (401 Unauthorized handling), and max retry limits.
- `config.py`: Explicitly typed configuration variables and environment bindings.

---

## 4. Verification & Testing Plan
- **Static Analysis & Linting:**
  - `uv run ruff check` (fix all linter warnings, clean up unused imports and syntax).
  - `uv run ruff format --check` (ensure 150 char line length compliance).
- **Type Checking:**
  - Enforce 100% strict type annotations across all files in `src/`.
  - Validate with `uv run mypy src` to guarantee zero type errors and zero bare `Any` in domain code.
- **Architectural Boundary Verification:**
  - Verify that `grep -r "print(" src/hikvision_downloader/core/` and `grep -r "input(" src/hikvision_downloader/core/` return 0 matches.
- **CLI Invariant & Smoke Test:**
  - Verify entry point `uv run hikvision-downloader` loads cleanly without import errors.
- **Approval Gate:**
  - Stop at the end of Phase 1 and wait for human approval before executing code changes.
