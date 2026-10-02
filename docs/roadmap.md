# Project Roadmap & Implementation Milestones

## 1. Vision & Release Strategy

The ultimate goal of Hikvision Downloader is to provide a **public, production-grade, cross-platform tool** that empowers anyone to reliably query and download CCTV recordings from Hikvision NVR systems over local networks without encountering the limitations and crashes of native browser interfaces.

### Dual Distribution Pipeline
1. **PyPI Python Package:**
   - Installable via `pip install hikvision-downloader` or `uv tool run hikvision-downloader`.
   - Exposes a standalone `hikvision-downloader` CLI command in the system `PATH`.
2. **Standalone Desktop Executables:**
   - Bundled GUI applications for **macOS** (`.dmg` / `.app`) and **Windows** (`.exe` installer) produced automatically by GitHub Actions.
   - Zero Python runtime or virtual environment setup required for end users.

---

## 2. Phased Development Roadmap

```
Phase 1: Docs Modularization & Architecture Contract (Task 002) [CURRENT]
   │
Phase 2: Core Decoupling & Dataclass Contract (Task 003)
   │
Phase 3: Testing & Fixture-Based Mocking Suite (Task 004)
   │
Phase 4: Headless CLI Engine & Entry Point (Task 005)
   │
Phase 5: NVR Authentication, ISAPI Auto-Discovery & Concurrent Engine (Task 006)
   │
Phase 6: PySide6 Native Desktop GUI & Secure OS Credential Store (Task 007)
   │
Phase 7: Packaging, CI/CD, & Public Release (Task 008)
```

---

### Phase 1: Documentation Modularization & Synchronization
- **Task ID:** `002-docs-modularization`
- **Status:** **Completed / Active**
- **Deliverables:**
  - Decompose legacy monolithic `TODO.md` into `docs/requirements.md`, `docs/architecture.md`, and `docs/roadmap.md`.
  - Ensure all problem statements, architecture flows, and packaging goals from `README.md` and `docs/hld-plan.md` are formally captured.
  - Remove `docs/TODO.md` upon approval.

---

### Phase 2: Core Service Decoupling & Dataclass Contract
- **Task ID:** `003-core-decoupling`
- **Status:** Planned
- **Deliverables:**
  - Restructure `src/hikvision_downloader/` into `core/`, `cli/`, and `ui/`.
  - Isolate all business logic (`dates.py`, `cameras.py`, `recordings.py`, `downloads.py`) from presentation logic.
  - Eliminate all `print()`, `input()`, and CLI interactions from `core/`.
  - Introduce pure dataclasses in `core/models.py` (`Camera`, `RecordingDate`, `Recording`, `DownloadProgress`, `DownloadResult`).
  - Implement standard progress callback protocols and cancellation tokens in download methods.

---

### Phase 3: Comprehensive Unit Testing & Fixture Mocking
- **Task ID:** `004-testing-suite`
- **Status:** Planned
- **Deliverables:**
  - Configure `pytest`, `pytest-cov`, and `pytest-mock` via `pyproject.toml`.
  - Build synthetic XML fixtures for ISAPI `dailyDistribution` and `CMSearch` responses.
  - Test date discovery across calendar boundaries (month transitions, leap years).
  - Test search pagination, XML parsing, and malformed payload handling.
  - Test download streaming, `.part` temporary file handling, deduplication/skipping, and network error recovery.
  - Ensure 100% offline test execution with zero live NVR hardware dependency.

---

### Phase 4: Headless CLI Engine & Console Entry Point
- **Task ID:** `005-cli-engine`
- **Status:** Planned
- **Deliverables:**
  - Implement structured CLI argument parser (via `argparse` or `click`) supporting both interactive prompts and headless automated batch mode.
  - Command-line flags: `--host`, `--date`, `--camera`, `--stream`, `--range`, `--output-dir`, `--non-interactive`, `--verbose`.
  - Rich terminal formatting with clean tabular output, elapsed time, and download speed indicators.
  - Define `hikvision-downloader` entry point in `[project.scripts]` inside `pyproject.toml`.

---

### Phase 5: NVR Authentication, ISAPI Auto-Discovery & Concurrent Engine
- **Task ID:** `006-auth-discovery-concurrency`
- **Status:** Planned
- **Deliverables:**
  - Replace manual `HIKVISION_COOKIE` extraction with automated username and password authentication over ISAPI (challenge/response & session cookie acquisition).
  - In-memory session renewal on HTTP 401 response.
  - **ISAPI Dynamic Camera Auto-Discovery:** Query NVR channels and track configurations dynamically via ISAPI endpoints, removing the strict need for manual TOML editing while retaining TOML as an optional override.
  - **Concurrent Multi-Stream Downloads:** Implement a thread pool worker for high-bandwidth LAN batch downloading with thread-safe progress aggregation and rate calculation.
  - Preserve `.env` session cookie support strictly as an optional developer override.
  - Enforce zero credential logging or exposure.

---

### Phase 6: PySide6 Native Desktop GUI & Secure OS Credential Store
- **Task ID:** `007-pyside6-desktop-ui`
- **Status:** Planned
- **Deliverables:**
  - Build native PySide6 (Qt 6) desktop interface with modern styling.
  - Interactive calendar date picker highlighting available recording dates.
  - Camera and stream dropdown selectors populated automatically via ISAPI discovery.
  - Search results table view with select-all, range selection, and individual segment checkboxes.
  - Real-time download progress bar, multi-segment concurrency progress, transfer rate (Mbps), time remaining, and Cancel button.
  - Dedicated `QThread` background workers ensuring zero UI thread blocking.
  - **Secure OS Credential Storage:** Persist NVR connection profiles and passwords securely using system keychains (`keyring` / Apple Keychain / Windows Credential Manager).
  - Settings dialog for NVR IP, credentials, output directory selection, and concurrency limits.

---

### Phase 7: Packaging, CI/CD, & Public Release
- **Task ID:** `008-packaging-cicd-release`
- **Status:** Planned
- **Deliverables:**
  - Set up GitHub Actions CI matrix testing (macOS, Windows, Ubuntu) for linting, type-checking (`mypy`), and pytest suites.
  - Configure standalone desktop builds using PyInstaller / PySide6 deployment tools producing `.app`/`.dmg` (macOS) and `.exe` (Windows).
  - Add official open-source license (`LICENSE`) and third-party dependency attribution (PySide6 LGPLv3 notices).
  - Publish build release workflow triggering on Git tags (`v1.0.0`) to upload GitHub Release binary assets and publish wheels to PyPI.

---

## 3. Future Enhancements (Post-v1)

- **Embedded Video Preview:** Integrated lightweight video player (via `QtMultimedia` or VLC bindings) to preview segments before downloading.
- **Multi-NVR Profile Manager:** Store and switch between multiple remote/local NVR profiles in the desktop UI.
- **In-App Auto-Updater:** Check for new GitHub Releases directly from the desktop application.
- **Bandwidth Throttling:** Configurable download rate limiter for congested network links.

---

## 4. Definition of Done for Public v1 Release

- [ ] **Security & Sanitization:** Zero hardcoded credentials, session tokens, or private IP addresses in codebase, tests, or documentation.
- [ ] **Core Decoupling:** Core services in `core/` have zero UI/CLI imports or side effects.
- [ ] **Automated Authentication & Keychain:** NVR login works automatically with username/password and secure OS keychain storage (`keyring`).
- [ ] **ISAPI Auto-Discovery:** Dynamic camera and track querying from NVR hardware out of the box.
- [ ] **Concurrent Downloads:** High-speed parallel segment streaming with atomic file safety.
- [ ] **Dual Interface:** Fully functional CLI and PySide6 Desktop GUI.
- [ ] **Testing:** 100% offline pytest suite with high test coverage across all core modules.
- [ ] **Static Quality:** Passes `ruff check`, `ruff format --check`, and `mypy` with zero warnings.
- [ ] **Cross-Platform Standalone Binaries:** Working macOS (`.dmg`/`.app`) and Windows (`.exe`) installers.
- [ ] **Public Packaging:** Publishable to PyPI via `pyproject.toml` with working `hikvision-downloader` CLI command.
- [ ] **Documentation:** Accurate `README.md`, `docs/requirements.md`, `docs/architecture.md`, `docs/roadmap.md`, and `LICENSE`.
