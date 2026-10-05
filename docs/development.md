# Hikvision Recording Downloader — Technical Development Guide

This document contains internal architecture notes, module responsibilities, developer workflows, and design details for `hikvision-downloader`.

---

## 1. How It Works (Internal Architecture)

```
                    ┌─────────────────────┐
                    │   Hikvision NVR     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Date Discovery     │
                    │                     │
                    │ Current month       │
                    │ Previous month      │
                    │ Previous-previous   │
                    │ (when applicable)   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Available Dates     │
                    │                     │
                    │ 2026-09             │
                    │ 01 02 03 ... 30     │
                    │                     │
                    │ 2026-08             │
                    │ 30 31               │
                    └──────────┬──────────┘
                               │
                         Select date
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Camera Selection    │
                    │                     │
                    │ D1 MainGate         │
                    │ D2 MainEntrance     │
                    │ D3 Office           │
                    │ ...                 │
                    └──────────┬──────────┘
                               │
                         Select stream
                               │
                         ┌─────┴─────┐
                         │           │
                        HD          SD
                         │           │
                         └─────┬─────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Recording Search    │
                    │                     │
                    │ NVR CMSearch API    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Recording List      │
                    │                     │
                    │ 1  start ... size   │
                    │ 2  start ... size   │
                    │ 3  start ... size   │
                    │ ...                 │
                    └──────────┬──────────┘
                               │
                       Select files
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Download Engine     │
                    │                     │
                    │ Existing → skip     │
                    │ New → download      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Organized Archive   │
                    └─────────────────────┘
```

---

## 2. Typical Workflow

1. **Date Discovery:**
   - Queries NVR ISAPI daily-distribution endpoints (`/ISAPI/ContentMgmt/record/daily-distribution/...`).
   - Parses `<record>true</record>` indicators.
   - Evaluates current and previous months. If the previous month contains recordings, older months are queried as applicable.
2. **Camera and Stream Track Mapping:**
   - Discovers available cameras dynamically from `/ISAPI/ContentMgmt/InputProxy/channels` or `/ISAPI/System/Video/inputs/channels`.
   - Maps camera channel IDs and dual-stream track IDs (`HD` = main stream, `SD` = sub stream).
3. **Recording Search:**
   - Generates XML CMSearch requests with pagination (`maxResults`, `searchResultPostion`).
   - Collects recording segment metadata (`trackID`, `startTime`, `endTime`, `playbackURI`, `sourceURI`, `fileSize`).
4. **Resilient Download & Storage:**
   - Downloads segments concurrently (1 to 4 worker pool).
   - Writes to temporary `.part` files.
   - Verifies HTTP 200/206 stream completion and renames to final `.mp4`.
   - Saves accompanying metadata CSV (`*_recording-list.csv`).

---

## 3. Project Structure & Responsibilities

The codebase is strictly structured into domain-specific packages:

```
src/
└── hikvision_downloader/
    ├── __init__.py
    ├── core/                  # Pure domain logic (zero UI/CLI dependencies)
    │   ├── __init__.py
    │   ├── auth.py            # Authentication, Keychain & session management
    │   ├── cameras.py         # Camera discovery and track mapping
    │   ├── dates.py           # Daily distribution & calendar discovery
    │   ├── downloads.py       # Concurrent multi-worker download engine
    │   ├── http_client.py     # Resilient HTTP session & retry policies
    │   ├── models.py          # Strict Pydantic domain models & semantic types
    │   └── recordings.py      # ISAPI CMSearch query builder and parser
    ├── cli/                   # Rich Terminal CLI Application
    │   ├── __init__.py
    │   ├── app.py             # CLI entrypoint & argument parser
    │   ├── formatters.py      # Rich tables, metric formatters & progress
    │   └── interactive.py     # Interactive prompts & wizard flows
    └── ui/                    # PySide6 Modern Desktop GUI
        ├── __init__.py
        ├── keychain.py        # Native OS Keychain UI wrapper
        ├── main_window.py     # Main application window & event orchestrator
        ├── models.py          # UI state, metric pills & table models
        ├── settings.py        # Connection profile management dialog
        ├── theme.py           # Dark & Light ergonomics, palette & stylesheet
        └── workers.py         # Non-blocking QThread background workers
```

### Module Responsibilities:

- **`core/auth.py`**: Handles HTTP Basic/Digest authentication discovery, token/cookie handling, and integration with OS Keychain services via `keyring`.
- **`core/cameras.py`**: Performs dynamic camera capability discovery over ISAPI with fallback to local `config/cameras.toml`.
- **`core/dates.py`**: Fetches and parses monthly recording availability calendars without brute-force queries.
- **`core/recordings.py`**: Handles pagination, XML payload generation, and response parsing for NVR recording search endpoints.
- **`core/downloads.py`**: Implements atomic chunked streaming, `.part` buffering, integrity checks, and worker thread pools.
- **`core/http_client.py`**: Centralizes session configuration, backoff retry logic, and connection timeout management.

---

## 4. Development & Testing Workflow

### Setting Up Development Environment:
```bash
# Clone the repository
git clone https://github.com/Sudhakar77777/hikvision-downloader.git
cd hikvision-downloader

# Install all dependencies (including dev and extra tools) via uv
uv sync --all-extras --dev
```

### Code Quality & Standards:
- **Formatting:** `uv run ruff format .`
- **Linting:** `uv run ruff check .`
- **Type Checking:** `uv run mypy src tests`

### Executing the Test Suite:
```bash
# Run headless test suite
QT_QPA_PLATFORM=offscreen uv run pytest

# Run integration tests (requires live NVR hardware specified in .env)
uv run pytest -m "integration"
```

### Building Distribution Packages:
```bash
uv build
```
