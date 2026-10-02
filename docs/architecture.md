# Architecture & Design Document

## 1. High-Level Architecture

Hikvision Downloader is structured as a decoupled, layered system where the core domain logic, transport layer, and presentation interfaces remain strictly separated.

```
                      ┌─────────────────────────────────────────┐
                      │          Presentation Layer             │
                      │  ┌───────────────────┬────────────────┐ │
                      │  │  PySide6 GUI      │    CLI Layer   │ │
                      │  │  (Desktop App)    │ (Terminal App) │ │
                      │  └─────────┬─────────┴────────┬───────┘ │
                      └────────────┼──────────────────┼─────────┘
                                   │                  │
                                   ▼                  ▼
                      ┌─────────────────────────────────────────┐
                      │          Application Core               │
                      │  ┌───────────────┬───────────────────┐  │
                      │  │ DateDiscovery │ CameraProfileMgr  │  │
                      │  ├───────────────┼───────────────────┤  │
                      │  │ SearchEngine  │ DownloadEngine    │  │
                      │  ├───────────────┴───────────────────┤  │
                      │  │         Domain Models             │  │
                      │  └─────────────────┬─────────────────┘  │
                      └────────────────────┼────────────────────┘
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │        HTTP & Transport Layer           │
                      │  ┌───────────────────────────────────┐  │
                      │  │  SessionMgr & Request Retries     │  │
                      │  └─────────────────┬─────────────────┘  │
                      └────────────────────┼────────────────────┘
                                           │  ISAPI / HTTP
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │             Hikvision NVR               │
                      └─────────────────────────────────────────┘
```

---

## 2. Directory Layout & Module Responsibilities

The codebase organizes modules by domain and responsibility:

```
src/hikvision_downloader/
├── core/
│   ├── __init__.py
│   ├── models.py          # Pure dataclasses and domain type contracts
│   ├── dates.py           # Daily distribution XML generation, parsing, & search
│   ├── cameras.py         # Dynamic ISAPI channel discovery & TOML profile resolution
│   ├── recordings.py      # CMSearch XML generation, parsing, & pagination
│   ├── downloads.py       # URL construction, streaming I/O, concurrent pool, & atomic .part management
│   └── auth.py            # ISAPI authentication, session lifecycle, & OS keychain (keyring) management
│
├── cli/
│   ├── __init__.py
│   ├── app.py             # CLI entry point, argument parsing, & command routing
│   ├── interactive.py     # Interactive terminal workflow & user prompts
│   └── formatters.py      # Terminal tables, colors, & summary printing
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py     # Main Qt Application window & tab orchestrator
│   ├── dates_view.py      # Calendar-based recording date selector widget
│   ├── recordings_view.py # QTableView with checkboxes, sorting, & batch selector
│   ├── settings_view.py   # NVR connection, credentials, & output path settings
│   └── workers.py         # QThread / QRunnable non-blocking background workers
│
├── http_client.py         # HTTP session factory, request retries, & error handling
├── config.py              # Configuration loaders and environment variable bindings
└── __init__.py
```

---

## 3. Domain Types & Data Models

To enforce strict type safety, prevent primitive obsession (`int`/`str` everywhere), and ensure self-documenting code, Hikvision Downloader defines explicit domain types, enumerations, and immutable models.

### 3.1 Domain Primitive Types & Enumerations
```python
from enum import StrEnum
from typing import NewType
from pydantic import BaseModel, SecretStr, Field

# Domain-specific semantic types
TrackId = NewType("TrackId", int)
CameraNumber = NewType("CameraNumber", int)
ByteCount = NewType("ByteCount", int)
MegabitsPerSecond = NewType("MegabitsPerSecond", float)
ISODatetimeStr = NewType("ISODatetimeStr", str)
NVRHost = NewType("NVRHost", str)

class StreamType(StrEnum):
    """Internal stream identifier."""
    MAIN = "main"
    SUB = "sub"

class StreamQuality(StrEnum):
    """Human-readable display/archive stream descriptor."""
    HD = "HD"
    SD = "SD"
```

### 3.2 Camera Profile Model
```python
@dataclass(frozen=True)
class Camera:
    number: CameraNumber
    name: str
    ip_address: str
    main_track: TrackId
    sub_track: TrackId

    @property
    def display_name(self) -> str:
        """Formatted camera name matching NVR UI (e.g., 'D1 MainGate')."""
        return f"D{self.number} {self.name}"

    @property
    def archive_name(self) -> str:
        """Sanitized folder-safe name (e.g., 'D1_MainGate')."""
        return f"D{self.number}_{self.name}"

    def stream_quality(self, stream: StreamType) -> StreamQuality:
        """Map stream type to user-facing quality enum."""
        return StreamQuality.HD if stream == StreamType.MAIN else StreamQuality.SD

    def track_id(self, stream: StreamType) -> TrackId:
        """Return the NVR track ID for the specified stream type."""
        if stream == StreamType.MAIN:
            return self.main_track
        if stream == StreamType.SUB:
            return self.sub_track
        raise ValueError(f"Unknown stream type: {stream}")
```

### 3.3 Recording Date Model
```python
@dataclass(frozen=True)
class RecordingDate:
    year: int
    month: int
    day: int

    @property
    def value(self) -> date:
        return date(self.year, self.month, self.day)

    @property
    def iso(self) -> ISODatetimeStr:
        return ISODatetimeStr(self.value.isoformat())
```

### 3.4 Recording Segment Model
```python
@dataclass(frozen=True)
class Recording:
    start: ISODatetimeStr
    end: ISODatetimeStr
    name: str
    size_bytes: ByteCount
    playback_uri: str

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)
```

### 3.5 Authentication & Connection Models (Pydantic)
```python
class NVRAuthCredentials(BaseModel):
    """Encapsulates NVR credentials with secret masking."""
    host: str
    username: str
    password: SecretStr
    port: int = Field(default=80, ge=1, le=65535)

class NVRConnectionProfile(BaseModel):
    """Stored profile metadata."""
    name: str
    host: str
    username: str
    keyring_service: str = "hikvision_downloader"
```

### 3.6 Progress & Result Models
```python
@dataclass(frozen=True)
class DownloadProgress:
    current_index: int
    total_files: int
    filename: str
    bytes_downloaded: ByteCount
    file_size_bytes: ByteCount
    speed_mbps: MegabitsPerSecond
    elapsed_seconds: float
    is_skipped: bool = False

@dataclass(frozen=True)
class DownloadResult:
    success: bool
    total_files: int
    downloaded_files: int
    skipped_files: int
    downloaded_bytes: ByteCount
    total_duration_seconds: float
    failed_index: int | None = None
    error_message: str | None = None
```

---

## 4. Communication & Async Execution Patterns

### 4.1 Core Callback Protocol
The core download engine does not depend on any specific UI or CLI library. It communicates real-time progress via callable protocols:

```python
ProgressCallback = Callable[[DownloadProgress], None]

def download_recordings(
    session: requests.Session,
    recordings: list[Recording],
    track_id: TrackId,
    output_dir: Path,
    start: int,
    count: int,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> DownloadResult:
    ...
```

### 4.2 PySide6 Asynchronous Worker Pattern
In the desktop GUI, background operations (date discovery, CMSearch, and media downloads) are executed inside a dedicated `QThread` to prevent blocking the Qt event loop:

```
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│         Main UI Thread          │           │       DownloadWorkerThread      │
│  (PySide6 MainWindow & Widgets) │           │         (QThread Worker)        │
└────────────────┬────────────────┘           └────────────────┬────────────────┘
                 │                                             │
                 │ 1. start_download(selection)                │
                 ├────────────────────────────────────────────►│
                 │                                             │ 2. Core download loop
                 │                                             │    updates chunk progress
                 │ 3. emit signal_progress(DownloadProgress)   │
                 │◄────────────────────────────────────────────┤
                 │ 4. Update UI progress bar & speed label     │
                 │                                             │
                 │ 5. emit signal_finished(DownloadResult)     │
                 │◄────────────────────────────────────────────┤
                 │ 6. Display completion notification          │
                 │                                             │
```

---

## 5. Storage & File System Conventions

### 5.1 Directory Schema
All downloads are archived systematically into predictable directory paths:
```
output/
└── <YYYYMMDD>_<archive_name>_<STREAM>/
    ├── 1_<recording_name>.mp4
    ├── 2_<recording_name>.mp4
    ├── ...
    └── <YYYY-MM-DD>_<archive_name>_<STREAM>_recording-list.csv
```

Example:
```
output/
└── 20260915_D4_FirstFL_HD/
    ├── 1_ch04_20260915_000000.mp4
    ├── 2_ch04_20260915_001500.mp4
    └── 2026-09-15_D4_FirstFL_HD_recording-list.csv
```

### 5.2 Atomic Download Safety Invariant
1. Target file path calculated: `output_dir / "1_recording.mp4"`.
2. Existing file check: If file exists and size > 0, immediately return `is_skipped = True`.
3. In-progress file path: `output_dir / "1_recording.mp4.part"`.
4. Stream chunks (1MB) to `.part` file.
5. On completion, verify size > 0 and atomically rename `.part` -> `.mp4`.
6. On exception or cancellation, unlink the `.part` file.

---

## 6. Architectural Invariants & Boundaries

1. **Strict Presentation Decoupling:** Files in `core/` must NEVER import `PySide6`, `click`, `rich`, or invoke `print()` / `input()`.
2. **State Isolation:** Core services must not rely on global mutable singletons. Sessions and configuration parameters are passed explicitly to service functions.
3. **No Duplicate API Logic:** All ISAPI XML generation and HTTP endpoints are centralized within their respective `core/` modules.
4. **Resilient HTTP Transport:** All network calls funnel through `http_client.py` to enforce retry counts, backoff timings, and uniform timeout policies.

---

## 7. Testing Architecture & Verification Contracts

The testing suite is structured into dedicated tiers:
```
tests/
├── fixtures/     # Synthetic ISAPI XML payloads (daily distribution, CMSearch)
├── unit/         # Model validations, XML generation/parsing, and TOML loading
├── functional/   # Streaming downloads, .part atomicity, skip caching, and cancellation
└── integration/  # Live NVR hardware checks (tagged with @pytest.mark.integration)
```

### Execution Invariants:
1. **Offline Isolation:** All tests under `tests/unit/` and `tests/functional/` run 100% offline without network I/O.
2. **Graceful Degradation:** Integration tests requiring live hardware automatically skip when `.env` is absent or unreachable.
3. **Strict Typing:** All test functions, fixtures, and helpers enforce 100% type annotations with zero bare `Any`.

