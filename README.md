# HikVision Downloader

[![CI](https://github.com/Sudhakar77777/hikvision-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/Sudhakar77777/hikvision-downloader/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/hikvision-downloader)](https://pypi.org/project/hikvision-downloader/)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

A high-performance, concurrent CCTV footage downloader and management suite for HikVision Network Video Recorders (NVRs). 

Engineered to overcome web browser export freezes, concurrency bottlenecks, and manual batching fatigue, `hikvision-downloader` delivers a direct, multi-worker parallel download engine, authentic camera capability discovery, zero-trust OS Keychain credential security (Apple Keychain, Windows Credential Manager, and Linux Secret Service), and an ergonomic dark/light PySide6 desktop GUI alongside a rich scriptable terminal CLI.

---

## Key Features

- **True Multi-Worker Parallel Engine:** Concurrent download worker pool (1 to 4 streams) with dedicated authenticated sessions, chunked streaming, atomic `.part` buffering, automatic retry backoff, and duplicate skipping.
- **Dynamic ISAPI Camera Discovery:** Automatically queries live IP channels, authentic camera names (e.g., `MainGate`, `Office`), and HD (Main) / SD (Sub) track IDs directly over HikVision ISAPI without synthetic channel prefixes or required manual configuration.
- **Intelligent Calendar Discovery:** High-speed monthly recording availability scanning without brute-force day iteration.
- **Storage & Bandwidth Validation:** Real-time twin segment metrics, available target disk headroom calculations, and aggregated bandwidth speed gauges.
- **Modern Desktop GUI (PySide6):** Ergonomic desktop console featuring adaptive Dark and Light themes with custom QSS design tokens, interactive date pickers, recording tables, and multi-threaded progress tracking.
- **Rich Terminal CLI:** Interactive step-by-step console wizard or non-interactive headless CLI for automated batch archiving and cron jobs.
- **Zero-Trust Credential Security:** Native integration with Apple Keychain, Windows Credential Manager, and Linux Secret Service via `keyring`. Passwords and session cookies are never written in plain text.
- **Structured Metadata Manifests:** Automatically exports accompanying CSV recording manifests with timestamps, channel metadata, file sizes, and playback URIs.

---

## Quick Start & Installation

### Option A: Standard Installation via pip
```bash
pip install hikvision-downloader
```

### Option B: Ephemeral Execution via uvx (No Install Required)
```bash
uvx hikvision-downloader --help
```

---

## Usage Modes

### 1. Desktop GUI Application

Launch the desktop operator interface:
```bash
hikvision-downloader-gui
```

**Desktop GUI Capabilities:**
- **Connection Profile Manager:** Create, edit, and switch between multiple NVR endpoints securely stored in your OS Keychain.
- **Visual Calendar Discovery:** Instant visual indicators showing dates with recorded footage.
- **Recording Segment Grid:** Filter, sort, and batch-select video segments with live disk space calculations.
- **Live Transfer Console:** Real-time transfer throughput (MB/s), individual worker stream progress, and live operational logs.

---

### 2. Interactive Terminal Wizard

Launch the interactive CLI wizard:
```bash
hikvision-downloader
```

The interactive workflow guides you step-by-step:
1. Scan and select from available recording dates.
2. Select camera channel by name or ID.
3. Choose stream quality (HD Main Stream or SD Sub Stream).
4. Review segments and specify download range (e.g., `all`, `1-10`, `15 5`).

---

### 3. Headless Scripting & Automation

Automate batch exports and scheduled backups using CLI options:

```bash
# Download all recordings for a specific date from Camera 1 (HD) using 4 concurrent workers
hikvision-downloader --date 2026-09-15 --camera 1 --stream main -w 4 --non-interactive

# Export specific segment ranges with custom target directory
hikvision-downloader --date 2026-09-15 --camera MainGate --stream main --range 1-20 --output-dir /Volumes/CCTV_Archive --non-interactive
```

#### CLI Command Options Reference

| Option | Description |
|---|---|
| `--host <HOST>` | NVR IP address or hostname. |
| `--port <PORT>` | NVR HTTP/ISAPI port (default: `80`). |
| `-u, --username <USER>` | NVR username. |
| `-p, --password <PASS>` | NVR password. |
| `-w, --workers <1-4>` | Number of concurrent download workers (default: `2`). |
| `--date <YYYY-MM-DD>` | Target recording date in ISO format (`YYYY-MM-DD`). |
| `--camera <ID/NAME>` | Camera channel ID (e.g., `1`) or camera name (e.g., `MainGate`). |
| `--stream <main\|sub>` | Stream quality: `main` (HD) or `sub` (SD). |
| `--range <RANGE>` | Segment range: `all`, `START-END` (e.g. `1-10`), or `START COUNT` (e.g. `1 10`). |
| `--output-dir <PATH>` | Target export directory path. |
| `--refresh-cameras` | Force fresh camera capability discovery from NVR. |
| `--non-interactive` | Run in non-interactive batch mode (fails if required options are omitted). |
| `--version` | Display program version number and exit. |
| `-h, --help` | Display command documentation and exit. |

---

## Supported Hardware & Compatibility

`hikvision-downloader` connects directly over your local area network (LAN) using standard **HikVision ISAPI v2.0+** XML/HTTP protocols:

- **HikVision NVR Series:** DS-7600 series, DS-7700 series, DS-9600 series, and hybrid DVR/NVR appliances.
- **Compatible OEM Brands:** Annke, LTS, Hilook, Trendnet, and other OEM rebrands supporting HikVision ISAPI endpoints.
- **Authentication Protocols:** HTTP Basic and HTTP Digest authentication supported out-of-the-box.

---

## Security Posture & Privacy

- **Native Vault Storage:** Connection credentials stored via the GUI profile manager are routed directly to your operating system's native secure enclave:
  - **macOS:** Apple Keychain Services (`Security.framework`).
  - **Windows:** Windows Credential Manager (`wincred`).
  - **Linux:** Secret Service API / FreeDesktop DBus secret service (`libsecret`).
- **Zero Plaintext Secrets:** Passwords and session cookies are never written to disk files or printed to logs.
- **Local Network Isolation:** All communication occurs strictly between your local machine and your NVR endpoint. No telemetry, third-party cloud services, or external network requests are made.

---

## Documentation

For technical details, architecture specifications, and contributor guides, see:
- [Technical Development Guide](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/docs/development.md)
- [System Architecture](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/docs/architecture.md)
- [System Requirements](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/docs/requirements.md)
- [Product Roadmap](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/docs/roadmap.md)

---

## Licensing & Compliance

- **License:** Distributed under the **GNU Affero General Public License v3** (`AGPL-3.0-or-later`). See [LICENSE](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/LICENSE) for full license text.
- **Third-Party Notices:** See [THIRD_PARTY_NOTICES.md](file:///Volumes/MinionDev/Workspace/CCTV/hikvision-downloader/THIRD_PARTY_NOTICES.md) for PySide6 LGPLv3 dynamic linking disclosures and open-source library attributions.

Copyright (c) 2026 Arivedha. All rights reserved.
