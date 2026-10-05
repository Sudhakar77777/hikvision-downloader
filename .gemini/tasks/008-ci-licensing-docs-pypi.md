TASK SPECIFICATION: 008-ci-licensing-docs-pypi

Adhere strictly to `.gemini/rules/2-security.md` and `.gemini/rules/4-coding-standards.md` (100% type annotations, zero bare `Any`).

---

### 1. Licensing & Compliance (`LICENSE` & `THIRD_PARTY_NOTICES.md`)
- **Root `LICENSE`**:
  - Add the official GNU Affero General Public License v3 (`AGPL-3.0-or-later`) text.
  - Copyright: `Copyright (c) 2026 Arivedha. All rights reserved.`
- **`THIRD_PARTY_NOTICES.md`**:
  - Add compliance disclosure for PySide6 LGPLv3 (dynamic linking notice and explicit note that users are entitled to inspect and substitute compatible Qt libraries).
  - Add open-source library attributions (`requests`, `keyring`, `pydantic`, `rich`, `pytest`).
- **`pyproject.toml`**:
  - Update license metadata: `license = { text = "AGPL-3.0-or-later" }`.
  - Ensure classifiers include:
    - `"License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)"`
    - `"Programming Language :: Python :: 3.14"`

---

### 2. Customer-Facing Documentation Overhaul (`README.md` & `docs/`)
- Move existing technical development notes to `docs/development.md`.
- Transform root `README.md` into an operator- and user-oriented product showcase:
  - **Hero Header**: Title, badge shield row (CI status, Python 3.14, License AGPLv3, PyPI version).
  - **Product Overview**: Professional HikVision NVR CCTV footage downloader with concurrent multi-worker engine, native OS Keychain integration, and ergonomic dark/light PySide6 GUI.
  - **Features**: Real camera names, multi-worker parallel streaming, calendar distribution mapping, responsive summary metric pills, zero credential leaking.
  - **Quick Start (CLI)**:
    ```bash
    # Install via pip
    pip install hikvision-downloader

    # Or run ephemerally with uv
    uvx hikvision-downloader --help
    ```
  - **Desktop GUI**: Launch with `hikvision-downloader-gui`.
  - **Supported Hardware**: HikVision NVRs running ISAPI v2.0+ (DS-7600, DS-7700, DS-9600 series and compatible OEM rebrands).
  - **Security & Privacy**: Explanation of OS Keychain storage (Apple Keychain, Windows Credential Manager, Secret Service API).

---

### 3. GitHub Actions CI Matrix (`.github/workflows/ci.yml`)
Create `.github/workflows/ci.yml` running on `push` and `pull_request` against `main`:
- **Matrix OS**: `[macos-latest, windows-latest, ubuntu-latest]`
- **Python Version**: `3.14`
- **Tool**: `astral-sh/setup-uv`
- **Steps**:
  1. Checkout repository.
  2. Install `uv`.
  3. Install dependencies: `uv sync --all-extras --dev`.
  4. Run formatting check: `uv run ruff format --check .`.
  5. Run linter check: `uv run ruff check .`.
  6. Run strict type-check: `uv run mypy src tests`.
  7. Run headless test suite:
     - Linux: `xvfb-run -a uv run pytest` (or `QT_QPA_PLATFORM=offscreen uv run pytest`).
     - macOS & Windows: `uv run pytest` with `QT_QPA_PLATFORM=offscreen`.

---

### 4. PyPI Publishing Workflow with OIDC (`.github/workflows/publish-pypi.yml`)
Create `.github/workflows/publish-pypi.yml` triggering strictly on published GitHub Releases or tag push (`v*.*.*`):
- **Repository Binding**: `Sudhakar77777/hikvision-downloader`
- **Permissions**:
  ```yaml
  permissions:
    id-token: write  # Mandatory for PyPI Trusted Publishing (OIDC)
    contents: read