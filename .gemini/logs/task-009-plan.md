# Implementation Plan - Task 009: Standalone Packaging, Release Binaries & GitHub Pages

## 1. Overview & Objectives
Task 009 establishes production-grade packaging, automated CI binary release pipelines, and an operator-oriented GitHub Pages download portal for **HikVision Downloader**.

Key deliverables:
1. **Runtime Asset Path Resolution (`src/hikvision_downloader/paths.py`)**: Ensure assets (SVGs, icons, stylesheets) resolve correctly in both development mode and frozen PyInstaller extraction directories (`sys._MEIPASS`). Update UI loaders to utilize `get_asset_path()`.
2. **PyInstaller Packaging Specification (`packaging/`)**: Repeatable build configurations for macOS (`.app` / `.dmg`) and Windows (`.exe` / `.zip`), bundling assets and declaring hidden imports.
3. **Automated Binary Release Workflow (`.github/workflows/release-binaries.yml`)**: GitHub Actions release workflow triggering on `v*.*.*` tags to build and attach macOS `.dmg` and Windows `.zip` installers to GitHub Releases.
4. **GitHub Pages Download Portal (`docs/index.html`, `docs/styles.css`, `.github/workflows/deploy-pages.yml`)**: Responsive, dark-themed download portal with primary CTA buttons, screenshot preview carousel, CLI installation snippet, feature overview, and AGPLv3 footer, deployed via GitHub Actions.
5. **Testing & Quality Assurance**: Unit tests for path resolution under normal and monkeypatched frozen execution, full static typing (100% strict mypy), linting (ruff), and test suite verification.

---

## 2. Target Files to Create, Inspect, or Modify

### New Files
- `src/hikvision_downloader/paths.py`: Runtime asset path resolver.
- `packaging/hikvision-downloader.spec`: PyInstaller build specification file.
- `packaging/build_macos.sh`: macOS packaging script (creates `.app` and `.dmg`).
- `packaging/build_windows.ps1`: Windows packaging script (creates `.exe` and `.zip`).
- `packaging/generate_icons.py` / `packaging/assets/`: Icon generator or asset bundles for `.icns` and `.ico`.
- `.github/workflows/release-binaries.yml`: GitHub Actions binary release workflow.
- `docs/index.html`: GitHub Pages landing page.
- `docs/styles.css`: GitHub Pages landing page styling (Arivedha brand theme).
- `.github/workflows/deploy-pages.yml`: GitHub Pages automated deployment workflow.
- `tests/unit/test_paths.py`: Unit tests for `get_asset_path` under standard and frozen runtimes.

### Files to Modify
- `pyproject.toml`: Add `pyinstaller>=6.11.0` to dev dependencies group.
- `src/hikvision_downloader/ui/main_window.py`: Update asset path definitions to use `get_asset_path()`.

---

## 3. Proposed Logic and Technical Details

### 3.1. Asset Path Resolution (`src/hikvision_downloader/paths.py`)
- Implement `get_asset_path(relative_path: str | Path) -> Path`:
  - If `getattr(sys, "frozen", False)` is True:
    - Determine extraction root `base_dir = Path(getattr(sys, "_MEIPASS", sys.executable)).resolve()`.
    - Check resolution candidates in order:
      1. `base_dir / relative_path`
      2. `base_dir / "hikvision_downloader" / relative_path`
      3. `base_dir / "ui" / "assets" / Path(relative_path).name`
      4. `base_dir / "assets" / Path(relative_path).name`
      5. Fallback to `base_dir / relative_path`.
  - If not frozen (development/installed package):
    - Determine package root `base_dir = Path(__file__).resolve().parent`.
    - Check resolution candidates in order:
      1. `base_dir / relative_path`
      2. `base_dir / "ui" / "assets" / relative_path`
      3. Fallback to `base_dir / relative_path`.
- Implement `is_frozen() -> bool` helper.
- Update `src/hikvision_downloader/ui/main_window.py`:
  - Import `get_asset_path` from `hikvision_downloader.paths`.
  - `ASSETS_DIR = get_asset_path("ui/assets")`
  - `LOGO_SVG_PATH = get_asset_path("ui/assets/logo.svg")`
  - `FAVICON_SVG_PATH = get_asset_path("ui/assets/favicon.svg")`
  - `ARIVEDHA_LOGO_SVG_PATH = get_asset_path("ui/assets/arivedha_logo.svg")`

### 3.2. PyInstaller Packaging (`packaging/`)
- **`packaging/hikvision-downloader.spec`**:
  - Entry point: `src/hikvision_downloader/ui/main_window.py`.
  - Data bundling:
    - `('../src/hikvision_downloader/ui/assets', 'hikvision_downloader/ui/assets')`
    - `('../src/hikvision_downloader/ui/assets', 'assets')`
    - `('../src/hikvision_downloader/ui/assets', 'ui/assets')`
  - Hidden imports:
    - `keyring.backends`
    - `keyring.backends.macOS`
    - `keyring.backends.Windows`
    - `keyring.backends.SecretService`
    - `pydantic`
    - `pydantic_core`
    - `PySide6.QtCore`
    - `PySide6.QtGui`
    - `PySide6.QtWidgets`
    - `PySide6.QtSvg`
    - `PySide6.QtSvgWidgets`
  - `console=False` for windowed GUI execution.
  - macOS bundle configuration:
    - App Name: `HikVision Downloader.app`
    - Bundle ID: `com.arivedha.hikvision-downloader`
    - Copyright: `Copyright © 2026 Arivedha. All rights reserved.`
    - High-DPI support (`NSHighResolutionCapable = True`).
- **`packaging/build_macos.sh`**:
  - Clean build using `pyinstaller packaging/hikvision-downloader.spec --clean --noconfirm`.
  - Create DMG image using `hdiutil create` with standard layout and `/Applications` link.
  - Output: `dist/HikVision-Downloader-macOS.dmg`.
- **`packaging/build_windows.ps1`**:
  - Clean build on Windows.
  - Compress output folder or executable into `dist/HikVision-Downloader-Windows-x64.zip`.

### 3.3. Automated Binary Release Workflow (`.github/workflows/release-binaries.yml`)
- Trigger: Tag push matching `v*.*.*`.
- Permissions: `contents: write`.
- Matrix: `os: [macos-latest, windows-latest]`.
- Steps:
  1. `actions/checkout@v4`
  2. `astral-sh/setup-uv@v5` with caching.
  3. `uv python install 3.14`
  4. `uv sync --all-extras --dev` + `uv pip install pyinstaller`
  5. Run platform build script / PyInstaller spec.
  6. Upload built artifacts (`dist/*.dmg` on macOS, `dist/*.zip` on Windows) via `softprops/action-gh-release@v2`.

### 3.4. GitHub Pages Download Portal (`docs/index.html` & `.github/workflows/deploy-pages.yml`)
- **`docs/index.html` & `docs/styles.css`**:
  - Modern, responsive dark UI styled with Arivedha brand palette (`#0F172A`, `#162032`, `#1E6B7B`, `#38BDF8`, `#F37021`).
  - **Header & Navigation**: Brand logo, navigation items, GitHub repository badge/link.
  - **Hero Section**:
    - Value proposition: "High-Speed CCTV Video Archiving Made Effortless".
    - Dual download CTA buttons:
      - macOS: `https://github.com/Sudhakar77777/hikvision-downloader/releases/latest/download/HikVision-Downloader-macOS.dmg`
      - Windows: `https://github.com/Sudhakar77777/hikvision-downloader/releases/latest/download/HikVision-Downloader-Windows-x64.zip`
    - Interactive dark/light mode screenshot preview switcher showcasing `docs/assets/gui-dark.jpg` and `docs/assets/gui-light.jpg`.
  - **Feature Grid**:
    - Multi-Worker Parallel Engine.
    - Zero-Trust Keychain Security.
    - Smart Date & Camera Auto-Discovery.
    - Dual Desktop GUI & Headless CLI.
  - **CLI / Developers Section**:
    - Code snippet block with copy button: `pip install hikvision-downloader` / `uvx hikvision-downloader --help`.
  - **Footer**:
    - AGPLv3 License info, GitHub source link, Copyright © 2026 Arivedha.
- **`.github/workflows/deploy-pages.yml`**:
  - Triggers on `push` to `main` modifying `docs/**` or `.github/workflows/deploy-pages.yml` (and `workflow_dispatch`).
  - Permissions: `pages: write`, `id-token: write`.
  - Actions: `actions/configure-pages@v5`, `actions/upload-pages-artifact@v3` (`path: docs`), `actions/deploy-pages@v4`.

---

## 4. Verification and Testing Plan

1. **Unit Tests**:
   - Create `tests/unit/test_paths.py`:
     - Test normal execution resolves asset paths.
     - Test `sys.frozen` monkeypatching redirects resolution to temporary directory.
     - Test fallback resolution behavior.
   - Run complete test suite: `uv run pytest`.
2. **Static Analysis & Linting**:
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy src tests`
3. **Packaging Validation**:
   - Validate PyInstaller build locally or verify spec syntax.
4. **Documentation Review**:
   - Check all updated docs and workflow files for strict security (no hardcoded credentials) and rule compliance.
