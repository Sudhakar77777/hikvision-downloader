TASK SPECIFICATION: 009-standalone-packaging-release-ghpages

Strictly adhere to `.gemini/rules/2-security.md` and `.gemini/rules/4-coding-standards.md` (100% type coverage, zero bare `Any`).

---

### 1. Runtime Asset Path Resolution (`src/hikvision_downloader/paths.py`)
Create or update `paths.py` to handle both development runs and frozen PyInstaller execution:
- Implement a helper function `get_asset_path(relative_path: str) -> Path`:
  - Check if `getattr(sys, "frozen", False)` is True.
  - If frozen, resolve paths relative to `Path(sys._MEIPASS)` (PyInstaller temporary extraction directory).
  - If not frozen, resolve paths relative to `Path(__file__).resolve().parent`.
- Audit and update all QSS stylesheet loaders, SVG icon loaders, and asset paths across `src/hikvision_downloader/gui/` to use `get_asset_path()`.
- Add unit tests verifying `get_asset_path()` returns valid paths in standard execution and correctly redirects when `sys.frozen` is monkeypatched in tests.

---

### 2. PyInstaller Packaging Specifications (`packaging/`)
Create a dedicated `packaging/` directory containing repeatable build specs:

- **Entrypoints**:
  - Target: GUI launcher (`hikvision_downloader.gui.main:main`).
- **`packaging/hikvision-downloader.spec`**:
  - Bundle GUI assets, icons (`.icns`, `.ico`, `.svg`), and QSS theme files into `assets/`.
  - Include hidden imports for `keyring.backends`, `pydantic`, `PySide6.QtCore`, `PySide6.QtGui`, `PySide6.QtWidgets`.
  - Set `console=False` for windowed GUI execution.
- **Platform Packaging Scripts**:
  - **macOS (`packaging/build_macos.sh`)**:
    - Build standalone `.app` bundle.
    - Package the `.app` into a clean drag-and-drop `.dmg` using `create-dmg` or `hdiutil`.
    - Set application bundle ID (`com.arivedha.hikvision-downloader`) and human-readable copyright.
  - **Windows (`packaging/build_windows.ps1` or build step)**:
    - Build single-file or directory `.exe` with embedded icon and version metadata.
    - Zip artifact as `hikvision-downloader-windows-x64.zip`.

---

### 3. Automated Binary Release Workflow (`.github/workflows/release-binaries.yml`)
Create `.github/workflows/release-binaries.yml`:
- **Triggers**: Tag push matching `v*.*.*`.
- **Permissions**: `contents: write`.
- **Matrix Strategy**:
  - `macos-latest` (builds `HikVision-Downloader-macOS.dmg`).
  - `windows-latest` (builds `HikVision-Downloader-Windows-x64.zip`).
- **Steps per runner**:
  1. Checkout code (`actions/checkout@v4`).
  2. Setup Python 3.14 via `astral-sh/setup-uv@v5` with caching.
  3. Install project dependencies and packaging tools (`uv sync --all-extras --dev`, install `pyinstaller`).
  4. Build binary distribution via `pyinstaller packaging/hikvision-downloader.spec`.
  5. Package into final installer (`.dmg` on macOS, `.zip` on Windows).
  6. Upload built artifacts to GitHub Release via `softprops/action-gh-release@v2`.

---

### 4. GitHub Pages Download Portal (`docs/index.html` & `.github/workflows/deploy-pages.yml`)
Create an operator-oriented web landing page deployed to GitHub Pages:
- **Design & Layout (`docs/index.html` + `docs/styles.css`)**:
  - Responsive, dark-themed modern UI matching the PySide6 app aesthetic.
  - **Hero Section**: App title, value proposition, and two primary CTA buttons:
    - `Download for macOS (.dmg)` $\rightarrow$ link pointing dynamically or statically to `https://github.com/Sudhakar77777/hikvision-downloader/releases/latest/download/HikVision-Downloader-macOS.dmg`.
    - `Download for Windows (.exe)` $\rightarrow$ link to `https://github.com/Sudhakar77777/hikvision-downloader/releases/latest/download/HikVision-Downloader-Windows-x64.zip`.
  - **Hero Screenshots**: Embed the sanitized dark and light mode UI screenshots.
  - **CLI / Developers Section**: Terminal code block featuring `pip install hikvision-downloader` and `uvx hikvision-downloader --help`.
  - **Feature Grid**: Parallel multi-worker engine, ISAPI camera discovery, OS Keychain zero-trust security.
  - **Footer**: AGPLv3 license disclaimer, copyright (c) 2026 Arivedha.
- **Deployment Workflow (`.github/workflows/deploy-pages.yml`)**:
  - Trigger on push to `main` when `docs/**` changes.
  - Deploy `docs/` folder to GitHub Pages using standard `actions/upload-pages-artifact@v3` and `actions/deploy-pages@v4`.

---

### 5. Verification Plan
- Verify `paths.py` passes all unit tests and existing test suite remains 100% green (`uv run pytest`).
- Verify PyInstaller spec builds locally without missing module errors (`uv run pyinstaller --dry-run` or test build).
- Run full linters and formatters:
  ```bash
  uv run ruff check .
  uv run ruff format --check .
  uv run mypy src tests