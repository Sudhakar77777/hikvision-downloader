# Task 008 Plan: CI Matrix, Licensing, Customer Documentation & PyPI Publishing

## 1. Analysis of Task Requirements

The goal of task `008-ci-licensing-docs-pypi` is to finalize production packaging, compliance, CI/CD automation, and customer-facing product documentation for `hikvision-downloader`:
1. **Licensing & Compliance**:
   - Create root `LICENSE` containing the full official GNU Affero General Public License v3 (`AGPL-3.0-or-later`) with copyright line: `Copyright (c) 2026 Arivedha. All rights reserved.`.
   - Create `THIRD_PARTY_NOTICES.md` documenting PySide6 LGPLv3 dynamic linking compliance (explicitly stating users can inspect and substitute compatible Qt libraries) and open-source library attributions (`requests`, `keyring`, `pydantic`, `rich`, `pytest`).
   - Update `pyproject.toml` with `license = { text = "AGPL-3.0-or-later" }` and classifiers for `AGPLv3+` and `Python 3.14`.
2. **Customer-Facing Documentation Overhaul**:
   - Move existing developer-oriented technical architecture notes from `README.md` to `docs/development.md`.
   - Rewrite root `README.md` as an operator- and user-oriented product showcase featuring:
     - Hero Header with badge shield row (CI status, Python 3.14, License AGPLv3, PyPI version).
     - Product Overview (HikVision NVR CCTV footage downloader with concurrent multi-worker engine, native OS Keychain integration, and PySide6 GUI).
     - Key Features (real camera names, parallel worker streaming, calendar distribution mapping, responsive summary metric pills, zero credential leaking).
     - Quick Start (CLI installation via `pip` and `uvx`).
     - Desktop GUI (`hikvision-downloader-gui`).
     - Supported Hardware (HikVision NVRs running ISAPI v2.0+).
     - Security & Privacy architecture (OS Keychain storage across Apple Keychain, Windows Credential Manager, and Secret Service API).
3. **GitHub Actions CI Matrix (`.github/workflows/ci.yml`)**:
   - Triggers on `push` and `pull_request` against `main`.
   - Matrix OS: `[macos-latest, windows-latest, ubuntu-latest]`.
   - Python Version: `3.14`.
   - Uses `astral-sh/setup-uv` with caching.
   - Steps: Checkout, setup uv, `uv sync --all-extras --dev`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src tests`, and headless `pytest` execution (`QT_QPA_PLATFORM=offscreen` / `xvfb-run -a`).
4. **PyPI Publishing Workflow with OIDC (`.github/workflows/publish-pypi.yml`)**:
   - Triggers on published GitHub Releases or tag push (`v*.*.*`).
   - Bound to `Sudhakar77777/hikvision-downloader`.
   - Configures `id-token: write` and `contents: read` for PyPI Trusted Publishing.
   - Builds distribution with `uv build` and publishes via `pypa/gh-action-pypi-publish@release/v1`.

---

## 2. Target Files to Create, Inspect, or Modify

### Target Files to Create:
- `LICENSE`: Full official GNU Affero General Public License v3 text with Arivedha copyright header.
- `THIRD_PARTY_NOTICES.md`: LGPLv3 dynamic linking disclosures for Qt/PySide6 and upstream third-party license acknowledgments.
- `docs/development.md`: Existing technical architecture, internal module breakdown, and developer notes.
- `.github/workflows/ci.yml`: GitHub Actions CI matrix workflow across macOS, Windows, and Ubuntu.
- `.github/workflows/publish-pypi.yml`: GitHub Actions PyPI trusted publishing workflow via OIDC.

### Target Files to Modify:
- `pyproject.toml`:
  - Update license table: `license = { text = "AGPL-3.0-or-later" }`.
  - Add classifiers list for `AGPLv3+` and `Python 3.14`.
- `README.md`: Transform into customer-facing showcase according to task specification.
- Python files requiring code formatting so `uv run ruff format --check .` passes seamlessly.

---

## 3. Proposed Logic & Content Details

### 3.1 `LICENSE`
- Standard GNU AGPLv3 text (Preamble + Terms & Conditions 1-17 + How to Apply Terms to Your New Programs).
- Header: `Copyright (c) 2026 Arivedha. All rights reserved.`

### 3.2 `THIRD_PARTY_NOTICES.md`
- **PySide6 / Qt Compliance Section**:
  - Explains that PySide6 is licensed under GNU LGPLv3.
  - States that `hikvision-downloader` dynamically links to PySide6 shared libraries without modification.
  - Clarifies user rights under LGPLv3: users are free to inspect, modify, and substitute compatible versions of Qt / PySide6 shared libraries in their virtual environment.
- **Third-Party Package Acknowledgments**:
  - `requests` (Apache-2.0)
  - `keyring` (MIT)
  - `pydantic` (MIT)
  - `rich` (MIT)
  - `pytest` (MIT)
  - `pytest-mock` (MIT)
  - `python-dotenv` (BSD-3-Clause)
  - `ruff` (MIT / Apache-2.0)
  - `mypy` (MIT)

### 3.3 `pyproject.toml`
```toml
license = { text = "AGPL-3.0-or-later" }
classifiers = [
    "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    "Programming Language :: Python :: 3.14",
    "Operating System :: OS Independent",
    "Environment :: X11 Applications :: Qt",
    "Topic :: Multimedia :: Video",
]
```

### 3.4 `docs/development.md` & `README.md`
- Preserve existing internal module diagrams (`downloader.py`, `dates.py`, `cameras.py`, `recordings.py`, `downloads.py`, `http_client.py`, `config.py`) in `docs/development.md`.
- Build a polished, user-focused `README.md` with:
  - Hero Header with badge shield row (CI status, Python 3.14, License AGPLv3, PyPI version).
  - Product Overview and feature showcase (concurrent downloads, calendar discovery, keychain security).
  - Quick Start CLI and GUI commands (`pip install hikvision-downloader`, `uvx hikvision-downloader --help`, `hikvision-downloader-gui`).
  - Supported Hardware list (HikVision ISAPI v2.0+ NVRs: DS-7600, DS-7700, DS-9600 series & OEMs).
  - Security & Privacy explanation (OS-native Keychain storage without plain-text storage).

### 3.5 `.github/workflows/ci.yml`
```yaml
name: CI Matrix

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Test (${{ matrix.os }}, Python ${{ matrix.python-version }})
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.14"]

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          version: "latest"

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync --all-extras --dev

      - name: Run code formatting check
        run: uv run ruff format --check .

      - name: Run linter check
        run: uv run ruff check .

      - name: Run strict type checking
        run: uv run mypy src tests

      - name: Run test suite (Linux with Xvfb)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update && sudo apt-get install -y libegl1 libgl1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xfixes0 libxcb-xinerama0 xvfb
          xvfb-run -a uv run pytest -m "not integration"

      - name: Run test suite (macOS & Windows offscreen)
        if: runner.os != 'Linux'
        env:
          QT_QPA_PLATFORM: offscreen
        run: uv run pytest -m "not integration"
```

### 3.6 `.github/workflows/publish-pypi.yml`
```yaml
name: Publish to PyPI

on:
  release:
    types: [published]
  push:
    tags:
      - "v*.*.*"

permissions:
  contents: read
  id-token: write  # Mandatory for PyPI Trusted Publishing (OIDC)

jobs:
  pypi-publish:
    name: Build and publish Python distribution to PyPI
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/hikvision-downloader
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "latest"

      - name: Set up Python
        run: uv python install 3.14

      - name: Build sdist and wheel
        run: uv build

      - name: Publish package distributions to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://upload.pypi.org/legacy/
```

---

## 4. Verification & Testing Plan

1. **Ruff Formatting & Linting**:
   - Run `uv run ruff format .` and verify `uv run ruff format --check .` exits 0.
   - Run `uv run ruff check .` and verify it exits 0.
2. **Mypy Strict Type Checking**:
   - Run `uv run mypy src tests` and verify 0 errors across all source and test files.
3. **Pytest Suite**:
   - Run `QT_QPA_PLATFORM=offscreen uv run pytest` and verify 100% test pass rate.
4. **Package Build Verification**:
   - Run `uv build` locally to verify valid `.whl` and `.tar.gz` generation with updated `pyproject.toml` metadata, `LICENSE`, and `README.md`.
