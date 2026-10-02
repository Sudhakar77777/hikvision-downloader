# Implementation Plan - Task 002: Modularize Documentation (Requirements, Architecture, Roadmap)

## 1. Task Analysis & Objectives
The goal of Task 002 is to decompose the monolithic `docs/TODO.md` into three structured, durable engineering documents under `docs/`:
- `docs/requirements.md`: Comprehensive functional and non-functional specifications.
- `docs/architecture.md`: Component layout, data models, decoupling rules, and async/callback contracts.
- `docs/roadmap.md`: Phased milestone plan, task mapping, and definition of done for public v1 release.

Once these documents are created and verified, `docs/TODO.md` will be slated for removal in Phase 3 to eliminate maintenance drift.

## 2. Target Files & Action Plan

| File | Operation | Description |
|---|---|---|
| `.gemini/logs/task-002-plan.md` | Create | This execution plan for Task 002. |
| `docs/requirements.md` | Create | Captures all functional (discovery, camera/stream, search, download, auth) and non-functional (security, cross-platform, UI/CLI dual mode, safe I/O) requirements. |
| `docs/architecture.md` | Create | Documents decoupled layer architecture (`core/`, `cli/`, `ui/`), data models (`Camera`, `RecordingDate`, `Recording`, `DownloadProgress`, `DownloadResult`), communication protocols, and file-system conventions. |
| `docs/roadmap.md` | Create | Defines the phased roadmap from Phase 1 to Phase 7, maps future task IDs, and sets the Definition of Done. |
| `.gemini/logs/task-002-walkthrough.md` | Create (Phase 2) | Verification walkthrough comparing created documents against initial specifications. |
| `docs/TODO.md` | Delete (Phase 3) | Decommission legacy monolithic TODO file after explicit user approval. |

## 3. Detailed Document Outlines

### A. `docs/requirements.md`
1. **Product Overview & Scope**: Purpose of Hikvision Downloader, problem statement (browser NVR interface limitations).
2. **Functional Requirements (FR)**:
   - FR-1: Automated Recording Date Discovery (NVR daily distribution query for current/previous months).
   - FR-2: Camera & Stream Profile Management (TOML configuration, HD/SD stream abstraction, future ISAPI auto-discovery).
   - FR-3: Recording Search & Metadata Extraction (CMSearch API query, pagination, ISO timestamps, byte size parsing, CSV export).
   - FR-4: Selective & Batch Downloading (Range selection `START COUNT`, full-batch, chunked streaming).
   - FR-5: Safe File Management & Deduplication (Atomic `.part` downloads, skip existing complete files, organized directory structure).
   - FR-6: Authentication & Session Handling (Development `.env` session cookie, production username/password login & session renewal).
3. **Non-Functional Requirements (NFR)**:
   - NFR-1: Dual Interface Support (Rich interactive CLI and native PySide6 desktop GUI).
   - NFR-2: Cross-Platform Compatibility (macOS and Windows first-class support; standalone packaging).
   - NFR-3: Security & Privacy Guardrails (Zero hardcoded credentials, RFC 5737 placeholder IPs, memory-only session tokens).
   - NFR-4: Performance & Network Resilience (Request retries, exponential backoff, configurable timeouts, bandwidth monitoring).
   - NFR-5: Testability & Offline Verification (Fixture-based mocked HTTP/XML tests, zero real-NVR dependency).

### B. `docs/architecture.md`
1. **High-Level Architecture**: Decoupled 3-tier structure (Core Engine, Presentation Interfaces [CLI/GUI], Infrastructure/HTTP Client).
2. **Component Breakdown**:
   - `core/`: Business logic isolated from presentation (`dates.py`, `cameras.py`, `recordings.py`, `downloads.py`, `auth.py`, `models.py`).
   - `cli/`: Interactive terminal orchestration, prompt handling, tabular output formatting.
   - `ui/`: PySide6 desktop application (`main_window.py`, `dates_view.py`, `recordings_view.py`, `settings_view.py`, worker threads).
   - `http/` (`http_client.py`): Session lifecycle, retry policies, HTTP error mapping.
3. **Domain Data Models (Dataclasses)**:
   - `Camera` (number, name, ip_address, main_track, sub_track, display/archive helpers).
   - `RecordingDate` (year, month, day, iso, date object).
   - `Recording` (start, end, name, size, playback_uri).
   - `DownloadProgress` (current_file, total_files, bytes_downloaded, total_bytes, speed_mbps, eta_seconds).
   - `DownloadResult` (success, files_downloaded, files_skipped, bytes_transferred, duration, failed_index).
4. **Communication & Execution Patterns**:
   - Callback protocol / generator streams for progress reporting in Core.
   - Background worker threads (`QThread` / `QRunnable`) in PySide6 to prevent UI freezing.
5. **Storage & Naming Conventions**:
   - Output directory hierarchy: `output/YYYYMMDD_D<camera_number>_<camera_name>_<stream>/`
   - File naming: `<index>_<recording_name>.mp4` and `<date>_D<num>_<name>_<stream>_recording-list.csv`.
6. **Architectural Invariants & Boundaries**:
   - Core must never import `PySide6`, use `input()`, or call `print()`.
   - No global mutable state; clients are explicitly instantiated.

### C. `docs/roadmap.md`
1. **Phased Development Milestones**:
   - **Phase 1: Documentation Modularization & Synchronization** *(Active - Task 002)*
   - **Phase 2: Core Decoupling & Dataclass Contract** *(Task 003: Isolate core logic, formalize models, eliminate print/input in core)*
   - **Phase 3: Testing & Mocked Fixtures Suite** *(Task 004: Unit tests for XML parsing, date discovery, search, download logic)*
   - **Phase 4: Headless CLI Engine & Script Entry Points** *(Task 005: CLI arguments, non-interactive batch mode, pyproject script entry point)*
   - **Phase 5: Automated NVR Authentication** *(Task 006: Username/password login, challenge-response, session management)*
   - **Phase 6: PySide6 Desktop GUI** *(Task 007: Calendar date picker, camera dropdown, table view, async downloader)*
   - **Phase 7: Packaging, CI/CD, & Public Release** *(Task 008: PyPI distribution, PyInstaller / PySide6 standalone binaries for macOS/Windows, GitHub Actions)*
2. **Future Enhancements (Post-v1)**:
   - ISAPI camera auto-discovery, concurrent multi-stream downloads, video preview playback, credential keychain storage.
3. **Definition of Done for Public v1 Release**:
   - Checklists for security, code architecture, testing, cross-platform packaging, licensing, and documentation.

## 4. Verification & Testing Plan
- **Verification of Document Completeness**: Cross-reference all 20 sections in `docs/TODO.md` to ensure zero information loss.
- **Security Audit**: Ensure all created documentation uses RFC 5737 placeholders (`192.168.1.100`, `admin`) and contains zero private IP addresses or credentials.
- **Ruff & Linter Checks**: Run `uv run ruff check` to ensure repository health remains pristine.
- **Lifecycle Stop**: Present Phase 1 plan and wait for explicit human approval before implementing Phase 2.
