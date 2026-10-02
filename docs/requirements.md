# Requirements Specification

## 1. Executive Summary & Purpose

### 1.1 Problem Statement
Hikvision Network Video Recorders (NVRs) provide a local web management portal (typically accessed via `http://<NVR-IP>/doc/page/login.asp`) to configure settings and export recorded CCTV footage over a local area network (LAN). However, extracting video files through this native browser interface is notoriously unreliable in real-world operations:
- **Frequent Freezes & Hangs:** Browser-based media streams frequently stall, buffer indefinitely, or crash mid-transfer, requiring full page reloads.
- **Strict Concurrency Limits:** The web portal restricts users to downloading only 2–3 files concurrently before choking network buffers or failing requests.
- **Painful Manual Batching:** Exporting a full day's footage (often 96+ 15-minute segments per camera) requires manual clicking, individual confirmations, and continuous babysitting for hours.

### 1.2 Solution & Value Proposition
**Hikvision Downloader** provides a robust, direct, and automated pipeline between the user's workstation and the Hikvision NVR over LAN by directly leveraging the Hikvision ISAPI (Intelligent Security API).

The core mission of this project is to provide a **reusable, public, cross-platform application** that anyone can use with ease to access and archive video recordings from Hikvision NVRs:
- **Dual-Interface Flexibility:** Accessible both as a lightweight, scriptable Command Line Interface (CLI) for engineers/automation and as a native desktop Graphical User Interface (GUI) built with PySide6/Qt for non-technical operators.
- **Public Packaging & Frictionless Distribution:**
  - Published to **PyPI (Python Package Index)** for immediate global installation via `pip install hikvision-downloader` or `uv tool run hikvision-downloader`, exposing a standalone binary CLI entry point in the user's `PATH`.
  - Distributed as standalone desktop application installers/binaries for **macOS** (`.dmg` / `.app`) and **Windows** (`.exe` / installer) via GitHub Releases, requiring zero Python setup from end users.
- **Resilient Batch Operations:** Directly queries the NVR's internal index, displays all segments, and downloads batches sequentially or selectively with automatic deduplication, retries, and atomic file safety.

---

## 2. Functional Requirements (FR)

### FR-1: Automated Recording Date Discovery
- **FR-1.1:** The system shall automatically discover which recent calendar dates contain recorded footage by querying the NVR's `dailyDistribution` ISAPI endpoint.
- **FR-1.2:** The discovery engine shall check the current month and the previous month. If the previous month contains at least one recorded day, it shall query the prior month (up to 3 months total) to prevent unnecessary historical queries.
- **FR-1.3:** The system shall parse `<record>true</record>` distribution elements and present only confirmed recording dates to the user.

### FR-2: Camera Profile & Stream Selection
- **FR-2.1:** The system shall support user-configurable camera profiles loaded from a local configuration file (`config/cameras.toml`).
- **FR-2.2:** Each camera profile shall define a camera number, human-readable name, IP address, main stream track ID (`main_track`), and sub-stream track ID (`sub_track`).
- **FR-2.3:** The user shall be able to choose between **HD** (Main Stream, high resolution) and **SD** (Sub Stream, standard resolution/bandwidth-friendly).
- **FR-2.4:** Internal NVR track IDs (e.g., `101`, `102`, `201`, `202`) shall remain an internal implementation detail and must not clutter user-facing selections or default folder paths.
- **FR-2.5:** The system shall support dynamic camera and channel auto-discovery directly from the NVR via ISAPI endpoints, removing the strict need for manual TOML editing while retaining TOML as an optional local configuration override.

### FR-3: Recording Search & Metadata Extraction
- **FR-3.1:** The system shall query the NVR's `CMSearch` ISAPI endpoint using the selected date and track ID.
- **FR-3.2:** The system shall handle pagination through recording search results to retrieve the complete inventory of matching video segments for the selected day.
- **FR-3.3:** The system shall extract segment start time, end time, segment file name, reported byte size, and RTSP playback URI from the XML search response.
- **FR-3.4:** The system shall generate a structured CSV manifest (`recording-list.csv`) for every search containing segment numbers, timestamps, sizes, and playback URIs, saved directly inside the target output archive directory.

### FR-4: Selective & Batch Downloading
- **FR-4.1:** The user shall have the option to download the entire day's recordings (all matching segments) in a single batch.
- **FR-4.2:** The user shall have the option to select a specific contiguous range of recordings using a `START COUNT` specification (e.g., `1 10` for files 1–10, `16 2` for files 16–17).
- **FR-4.3:** Video streams shall be downloaded in 1MB chunks with real-time transfer progress tracking, elapsed time calculation, and throughput measurement (Mbps).
- **FR-4.4:** The system shall support concurrent multi-stream downloads via a thread worker pool for high-bandwidth LAN operations, with aggregate throughput and progress monitoring.

### FR-5: Safe File Management & Deduplication
- **FR-5.1:** The system shall write in-progress downloads to temporary `.part` files (e.g., `1_recording.mp4.part`).
- **FR-5.2:** Upon successful completion and size verification, the system shall atomically rename `.part` files to their final `.mp4` destination.
- **FR-5.3:** If a transfer fails or is interrupted, the system shall clean up incomplete `.part` files.
- **FR-5.4:** The system shall inspect the target destination before initiating a download. If a completed non-empty file already exists, the download shall be skipped and logged as `SKIP`.
- **FR-5.5:** Output files shall be systematically organized by date, camera, and stream using the standard directory schema:
  `output/YYYYMMDD_D<camera_number>_<camera_name>_<stream>/`

### FR-6: Authentication & Session Management
- **FR-6.1 (Development / Testing):** The system shall support authenticating via an existing `HIKVISION_COOKIE` defined in `.env`.
- **FR-6.2 (Public v1 Goal):** The system shall authenticate against the NVR using user-supplied credentials (`NVR host`, `username`, `password`) over ISAPI, generating and refreshing the required WebSession cookie automatically without requiring browser inspection.
- **FR-6.3:** Passwords must never be written to source code, logged, or exposed in error messages.
- **FR-6.4:** Persistent credential storage (optional in CLI/GUI) shall use secure OS keychains (`keyring` / Apple Keychain / Windows Credential Manager) rather than plain text files.

---

## 3. Non-Functional Requirements (NFR)

### NFR-1: Dual Interface Architecture
- **NFR-1.1 Headless Core:** Core NVR services (`core/`) must remain 100% decoupled from any presentation layer. Core logic must never call `input()`, `print()`, or import Qt/UI modules.
- **NFR-1.2 Command Line Interface:** A terminal interface providing interactive prompts, clear ASCII/ANSI tables, progress indicators, and headless scriptability.
- **NFR-1.3 Desktop UI:** A modern, cross-platform PySide6 (Qt 6) application featuring interactive calendar date pickers, camera/stream selector dropdowns, tabular recording views with checkboxes, directory pickers, and asynchronous progress dialogs.

### NFR-2: Cross-Platform Compatibility & Distribution
- **NFR-2.1 Supported Platforms:** macOS (Apple Silicon & Intel) and Windows (x64) as primary targets; Linux compatible.
- **NFR-2.2 Standalone Packaging:** Desktop application bundles must be packaged with PyInstaller / PySide6 deployment tools so end users can run the GUI without installing Python or virtual environments.
- **NFR-2.3 PyPI Distribution:** Standard `pip` and `uv` package with clean entry points (`[project.scripts]`) for terminal users.

### NFR-3: Security & Privacy Guardrails
- **NFR-3.1 Zero Committed Credentials:** No private keys, passwords, live session tokens, or internal credentials in version control.
- **NFR-3.2 RFC 5737 Compliance:** All documentation, sample configs, and code examples must strictly use RFC 5737 reserved placeholder IPs (e.g., `192.168.1.100`) and sanitized generic camera names.
- **NFR-3.3 Credential Storage:** Active sessions stored in memory; persistent credentials (if saved by user choice in desktop UI) must utilize secure OS keychains (e.g., `keyring`).

### NFR-4: Performance & Network Resilience
- **NFR-4.1 Non-Blocking Execution:** Network I/O and streaming operations in the GUI must run inside dedicated worker threads (`QThread` / `QRunnable`) to maintain 60 FPS UI responsiveness.
- **NFR-4.2 Retries & Backoff:** Transient network interruptions and HTTP timeouts must trigger automatic retries (up to 3 attempts with 5-second backoff) before raising fatal errors.
- **NFR-4.3 Connection Timeouts:** Configurable request timeouts (default 120s) to prevent indefinite hangs during slow LAN streaming.

### NFR-5: Testability & Mock Fixtures
- **NFR-5.1 Zero Hardware Dependency in Tests:** All automated unit and integration tests must run 100% offline using captured XML responses, mock HTTP sessions, and file-system fixtures.
- **NFR-5.2 Comprehensive Coverage:** XML serializers, parsers, date calculators, range validators, and path generators must be covered with regression tests.

### NFR-6: Licensing & Compliance
- **NFR-6.1 Project License:** Explicit open-source license defined in repository (`LICENSE`).
- **NFR-6.2 Dependency Attribution:** Full audit and compliance documentation for third-party libraries, specifically adhering to PySide6 / Qt Community Edition LGPLv3 obligations.
