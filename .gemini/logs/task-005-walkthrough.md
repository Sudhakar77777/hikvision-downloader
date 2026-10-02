# Walkthrough - Task 005: Headless CLI Engine, Graceful Interruption & Console Entry Point

## 1. Overview & Objectives
The goal of Task 005 was to construct a robust, production-ready Command-Line Interface (CLI) in `src/hikvision_downloader/cli/` that supports both headless (scriptable/automated) execution and seamless interactive wizard fallback, complete with signal interruption handling (`SIGINT`/`Ctrl+C`), atomic `.part` file cleanup on abort, clear help documentation, and a working PyPI console script entry point.

---

## 2. Changes Implemented

### 2.1 CLI Application Engine (`src/hikvision_downloader/cli/app.py`)
- Created `build_argument_parser()` providing full CLI argument parsing with `RawDescriptionHelpFormatter`:
  - `--host`: Optional Hikvision NVR host / IP address override.
  - `--date`: Target recording date in `YYYY-MM-DD` format.
  - `--camera`: Camera channel number (e.g. `1`) or camera name (e.g. `FrontGate`).
  - `--stream`: Stream quality (`main` / `sub`, case-insensitive).
  - `--range`: Download range (`all`, `START-END`, `START:END`, or `START COUNT`).
  - `--output-dir`: Custom destination directory path.
  - `--non-interactive`: Headless automation flag (fails with exit code 1 if required parameters are missing).
  - `--version`: Displays version information (`hikvision-downloader 0.1.0`).
  - Comprehensive help description and epilog documenting `Ctrl+C` graceful interruption and `.part` file cleanup.
- Implemented helper utilities with 100% strict type annotations:
  - `parse_date_spec(date_str: str) -> date`: Validates and parses ISO date strings.
  - `parse_stream_type(stream_str: str) -> StreamType`: Parses and validates stream type.
  - `parse_range_spec(range_str: str | None, total: int) -> tuple[int, int]`: Flexible parser supporting `all`, `1-10`, `1:10`, `1 10`, and single numbers.
  - `resolve_camera(cameras: dict[CameraNumber, Camera], camera_spec: str | int) -> Camera`: Multi-strategy resolver supporting numeric channel, short name, display name, and archive name.
  - `setup_signal_handler(cancel_event: threading.Event) -> None`: Signal handler for `SIGINT` (`Ctrl+C`) that triggers cancellation token and displays abort notice.
  - `run_app(argv: Sequence[str] | None = None) -> int`: Orchestrates the complete headless and interactive flow, returning 0 on success, 1 on error, and 130 on user cancellation.
  - `main() -> None`: Standard entrypoint invoking `sys.exit(run_app())`.

### 2.2 CLI Formatters (`src/hikvision_downloader/cli/formatters.py`)
- Added `display_abort_notice() -> None`: Formatted banner displayed on user interruption.
- Added `display_error(message: str) -> None`: Formatted error message banner for CLI errors.

### 2.3 Package Exports & Script Entry Point
- Updated `src/hikvision_downloader/cli/__init__.py`: Exported all new CLI utilities (`build_argument_parser`, `main`, `run_app`, `parse_date_spec`, `parse_range_spec`, `parse_stream_type`, `resolve_camera`, `setup_signal_handler`, `display_abort_notice`, `display_error`).
- Updated `src/hikvision_downloader/downloader.py`: Delegated `main()` to `hikvision_downloader.cli.app:main`.
- Updated `pyproject.toml`: Configured `[project.scripts]` to point `hikvision-downloader = "hikvision_downloader.cli.app:main"`.

### 2.4 Unit Test Suite (`tests/unit/test_cli.py`)
- Added 31 unit tests covering:
  - Default CLI arguments and custom flag parsing.
  - `--help` formatting and epilog documentation.
  - Date parsing (valid ISO format, invalid format rejection).
  - Stream type parsing (`main`, `sub`, case insensitivity, rejection of invalid streams).
  - Range parsing (`all`, hyphen `1-10`, colon `1:10`, space `1 10`, single `5`, boundary checks, invalid formats).
  - Camera resolution by number, exact name, lower-case name, display name, and archive name.
  - `display_abort_notice` and `display_error` formatting.
  - `setup_signal_handler` and `cancel_event` activation.
  - Headless mode missing parameter validation (`--date`, `--camera`, `--stream`).
  - Headless mode successful download execution and error exit handling.
  - Interactive mode cancel paths (date cancelled, camera cancelled, stream cancelled, no recordings, confirmation declined).
  - Mid-download signal cancellation returning exit code 130.

---

## 3. Verification & Test Results

### 3.1 Pytest Test Suite
```bash
$ uv run pytest
============================= test session starts ==============================
platform darwin -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: /Volumes/MinionDev/Workspace/CCTV/hikvision-downloader
configfile: pyproject.toml
testpaths: tests
plugins: mock-3.16.0
collecting ... collected 86 items

tests/functional/test_cancellation.py ....                               [  4%]
tests/functional/test_download_engine.py ..........                      [ 16%]
tests/integration/test_live_nvr.py .                                     [ 17%]
tests/unit/test_cameras.py .......                                       [ 25%]
tests/unit/test_cli.py ...............................                   [ 61%]
tests/unit/test_dates.py .........                                       [ 72%]
tests/unit/test_models.py ..............                                 [ 88%]
tests/unit/test_recordings.py ..........                                 [100%]

============================== 86 passed in 0.20s ==============================
```

### 3.2 Static Type Checking (mypy) & Linting (ruff)
```bash
$ uv run mypy src tests && uv run ruff check .
Success: no issues found in 26 source files
All checks passed!
```

---

## 4. Invariant Compliance
- **100% Strict Type Annotations**: All new functions, arguments, and return types in `cli/app.py`, `cli/formatters.py`, and `tests/unit/test_cli.py` have explicit type annotations with zero bare `Any`.
- **Decoupled Architecture**: `core/` modules remain free of CLI dependencies (`print`, `input`), while `cli/` handles user presentation and interaction.
- **Graceful Interruption**: `SIGINT` (`Ctrl+C`) immediately activates the cancellation token, ensuring temporary `.part` files are unlinked and execution exits cleanly with status code 130 without tracebacks.
