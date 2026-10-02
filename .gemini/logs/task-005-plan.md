# Implementation Plan - Task 005: Headless CLI Engine, Graceful Interruption & Console Entry Point

## 1. Task Analysis & Requirements
Task 005 requires building a robust, production-ready Command-Line Interface (CLI) in `src/hikvision_downloader/cli/` that supports both headless (scriptable/automation) execution and interactive wizard fallback, complete with signal interruption handling (`SIGINT`/`Ctrl+C`), atomic `.part` cleanup on abort, clear help documentation, and a working PyPI console script entry point.

### Key Requirements:
1. **`src/hikvision_downloader/cli/app.py`**:
   - Argument parsing supporting:
     - `--host`: NVR host/IP override (defaults to `HIKVISION_HOST` from `.env`).
     - `--date`: ISO date `YYYY-MM-DD` (e.g. `2024-03-15`).
     - `--camera`: Camera channel number (e.g. `1`) or camera name (e.g. `FrontGate`).
     - `--stream`: Stream quality (`main` / `sub`, case-insensitive).
     - `--range`: Download range (`all`, `START-END` like `1-10`, `START:END` like `1:10`, or `START COUNT` like `1 10`).
     - `--output-dir`: Custom destination directory path.
     - `--non-interactive`: Boolean flag to run without interactive prompts.
   - Clear help documentation and epilog explaining how to abort execution (`Ctrl+C`).
   - Seamless interactive routing: when required parameters are omitted and `--non-interactive` is not specified, seamlessly route to `cli/interactive.py` for user input.
   - Non-interactive validation: when `--non-interactive` is specified, validate all required parameters and fail cleanly with exit code 1 if anything is missing or invalid.
2. **Graceful Interruption & Signal Handling**:
   - Register signal handler for `SIGINT` (`signal.signal(signal.SIGINT, ...)`).
   - Trap `KeyboardInterrupt` cleanly in orchestrator loops.
   - Immediate cancellation event notification (`cancel_event.set()`) so `core/downloads.py` unlinks temporary `.part` files immediately and exits without unhandled tracebacks.
   - Return exit code 130 on cancellation (standard Unix SIGINT exit code).
3. **`src/hikvision_downloader/cli/formatters.py`**:
   - Add `display_abort_notice()`: Formatted banner notifying the user that download has been aborted and temporary `.part` files are being cleaned up.
   - Add `display_error(message: str)`: Formatted error message banner.
4. **`pyproject.toml`**:
   - Update `[project.scripts]` to point `hikvision-downloader` to `hikvision_downloader.cli.app:main`.
5. **Tests (`tests/unit/test_cli.py`)**:
   - Unit tests covering argument parsing (all flags, defaults, invalid options, help/epilog).
   - Range parser tests (`all`, `1-10`, `1 10`, out of bounds, invalid format).
   - Date parser & camera resolver tests.
   - Non-interactive validation & error exit tests.
   - Signal handler & cancellation event tests.
   - CLI formatter tests (`display_abort_notice`, `display_error`).
6. **Strict Invariants**:
   - Adhere strictly to `.gemini/rules/1-workflow.md`, `2-security.md`, `3-design.md`, `4-coding-standards.md`, `5-review-guidelines.md`, and `6-skills.md`.
   - 100% type annotations on all parameters and return types across all new CLI files (zero bare `Any`).
   - Zero bare exceptions; no unhandled `KeyboardInterrupt` stack traces exposed to the user.

---

## 2. Target Files & Proposed Actions

| File | Operation | Description |
|---|---|---|
| `.gemini/logs/task-005-plan.md` | Create | This execution plan for Task 005. |
| `src/hikvision_downloader/cli/formatters.py` | Modify | Add `display_abort_notice` and `display_error` formatting helpers. |
| `src/hikvision_downloader/cli/app.py` | Create | Implement argument parser, range/date parsing, camera resolver, signal handling, and headless/interactive orchestrator. |
| `src/hikvision_downloader/cli/__init__.py` | Modify | Re-export CLI entry points (`main`, `run_app`, `build_argument_parser`, `display_abort_notice`, `display_error`). |
| `src/hikvision_downloader/downloader.py` | Modify | Delegate `main()` to `cli.app:main` for backward compatibility. |
| `pyproject.toml` | Modify | Update `[project.scripts]` to point `hikvision-downloader = "hikvision_downloader.cli.app:main"`. |
| `tests/unit/test_cli.py` | Create | Comprehensive unit tests for CLI argument parsing, range resolver, signal handling, and formatters. |
| `.gemini/logs/task-005-walkthrough.md` | Create (Phase 2) | Implementation walkthrough capturing test results and verification outputs. |

---

## 3. Detailed Logic & Architecture Design

### 3.1 `src/hikvision_downloader/cli/formatters.py` Additions
Add the following functions with strict type annotations:
- `display_abort_notice() -> None`:
  ```python
  def display_abort_notice() -> None:
      """Display a notification banner when execution is cancelled by user."""
      print()
      print("=" * 70)
      print("[ABORTED] Operation cancelled by user (Ctrl+C).")
      print("Cleaning up temporary download files...")
      print("=" * 70)
  ```
- `display_error(message: str) -> None`:
  ```python
  def display_error(message: str) -> None:
      """Display a formatted error message banner."""
      print()
      print("=" * 70)
      print(f"ERROR: {message}")
      print("=" * 70)
  ```

### 3.2 `src/hikvision_downloader/cli/app.py` Implementation
1. **Argument Parser (`build_argument_parser() -> argparse.ArgumentParser`)**:
   - Program name: `hikvision-downloader`
   - Description: `Hikvision CCTV NVR Recording Downloader - Headless & Interactive CLI`
   - Epilog:
     ```text
     Interruption:
       Press Ctrl+C at any time to gracefully abort downloads. In-flight temporary
       download files (.part) will be automatically cleaned up without leaving partial files.
     ```
   - Arguments:
     - `--host`: `str | None` - Hikvision NVR host / IP address override.
     - `--date`: `str | None` - Target recording date in `YYYY-MM-DD` format.
     - `--camera`: `str | None` - Camera channel number (e.g. `1`) or camera name (e.g. `FrontGate`).
     - `--stream`: `str | None` - Stream quality: `main` (HD) or `sub` (SD).
     - `--range`: `str | None` - Download range: `all`, `START-END` (e.g. `1-10`), or `START COUNT` (e.g. `1 10`).
     - `--output-dir`: `Path | None` - Target directory path for downloaded videos and recording lists.
     - `--non-interactive`: `bool` (action `store_true`) - Disallow interactive prompts and fail if required options are missing.
     - `--version`: `action="version"`, `version="%(prog)s 0.1.0"`.

2. **Parser and Helper Utilities**:
   - `parse_date_spec(date_str: str) -> date`: Parses `YYYY-MM-DD` into `datetime.date`, raises `ValueError` on bad format.
   - `parse_stream_type(stream_str: str) -> StreamType`: Parses `"main"` / `"sub"` (case-insensitive) into `StreamType.MAIN` or `StreamType.SUB`.
   - `parse_range_spec(range_str: str | None, total: int) -> tuple[int, int]`:
     - If `range_str is None` or `range_str.strip().lower() == "all"`: returns `(1, total)`.
     - Supports `"START-END"` (e.g. `"1-10"`), `"START:END"` (e.g. `"1:10"`), or `"START COUNT"` (e.g. `"1 10"`).
     - Validates `1 <= start <= end <= total` and `count >= 1`.
     - Raises `ValueError` with clear error explanations if invalid or out of bounds.
   - `resolve_camera(cameras: dict[CameraNumber, Camera], camera_spec: str | int) -> Camera`:
     - Tries matching numeric camera channel (`int(camera_spec)`).
     - Tries matching camera name or display name (case-insensitive comparison).
     - Raises `ValueError` if no match found.

3. **Signal Interruption Handler**:
   - `setup_signal_handler(cancel_event: threading.Event) -> None`:
     - Configures `signal.signal(signal.SIGINT, handler)`.
     - Handler sets `cancel_event.set()`, prints abort notice via `display_abort_notice()`.
     - Protects against multiple SIGINT calls with clean exit.

4. **Execution Flow (`run_app(argv: Sequence[str] | None = None) -> int`)**:
   - Initialize `cancel_event = threading.Event()` and configure signal handler.
   - Parse CLI arguments via `build_argument_parser()`.
   - Resolve NVR Host (from `--host` flag or `config.NVR_HOST`). If missing, print error and return 1.
   - Load cameras via `load_cameras(CAMERA_CONFIG)`.
   - Create HTTP session via `make_session()`.
   - **Date Resolution**:
     - If `--date` is provided: parse via `parse_date_spec`.
     - Else if `--non-interactive`: print error (`"--date is required in non-interactive mode"`) and return 1.
     - Else: call `discover_available_dates(session, host, ...)`, display available dates, and prompt via `ask_recording_date(months)`.
       - If user cancels / quits, return 0.
   - **Camera Resolution**:
     - If `--camera` is provided: resolve via `resolve_camera(cameras, args.camera)`.
     - Else if `--non-interactive`: print error (`"--camera is required in non-interactive mode"`) and return 1.
     - Else: prompt via `ask_camera(cameras)`.
       - If user cancels / quits, return 0.
   - **Stream Resolution**:
     - If `--stream` is provided: parse via `parse_stream_type(args.stream)`.
     - Else if `--non-interactive`: print error (`"--stream is required in non-interactive mode"`) and return 1.
     - Else: prompt via `ask_stream()`.
       - If user cancels / quits, return 0.
   - Display selection summary via `display_selection(camera, stream)`.
   - **Search Recordings**:
     - Query NVR for recordings matching date & stream track via `get_all_recordings(...)`.
     - If no recordings found: print message and return 0.
     - Save recording list CSV to `output_dir` via `save_recording_list(...)`.
     - Display recording list table via `display_recording_list(recordings)`.
   - **Range Selection**:
     - If `--range` is provided: parse via `parse_range_spec(args.range, len(recordings))`.
     - Else if `--non-interactive`: default to `(1, len(recordings))` (download all).
     - Else: prompt via `ask_download_selection(len(recordings))`.
       - If user cancels / quits, return 0.
       - Confirm download via `confirm_download(...)`. If declined, return 0.
   - **Download Execution**:
     - Call `download_recordings(...)` with `cancel_event` and `progress_callback=display_download_progress`.
     - If cancelled during execution (`cancel_event.is_set()`):
       - Return exit code 130.
     - If failed:
       - Display failure banner and return 1.
     - If success:
       - Display download summary via `display_download_summary(...)` and return 0.
   - Catch `KeyboardInterrupt` at top-level: set `cancel_event.set()`, display abort notice, and return 130.

### 3.3 `pyproject.toml` Update
- Update entry point:
  ```toml
  [project.scripts]
  hikvision-downloader = "hikvision_downloader.cli.app:main"
  ```

---

## 4. Verification and Testing Plan

### 4.1 Unit Tests (`tests/unit/test_cli.py`)
1. **Argument Parsing**:
   - Default values when invoked with no arguments.
   - Custom `--host`, `--date`, `--camera`, `--stream`, `--range`, `--output-dir`, `--non-interactive`.
   - `--help` outputs expected help text and epilog mentioning `Ctrl+C`.
2. **Range Parser (`parse_range_spec`)**:
   - None or `"all"` -> `(1, total)`.
   - `"1-10"` -> `(1, 10)`.
   - `"5:8"` -> `(5, 4)`.
   - `"16 2"` -> `(16, 2)`.
   - Error cases: `start < 1`, `count < 1`, `end > total`, malformed strings.
3. **Date Parser (`parse_date_spec`)**:
   - `"2024-03-15"` -> `date(2024, 3, 15)`.
   - Malformed date string (e.g. `"2024/03/15"`, `"invalid"`) raises `ValueError`.
4. **Camera Resolver (`resolve_camera`)**:
   - Numeric channel lookup (`1` or `"1"` -> `Camera` D1).
   - Name lookup (`"FrontGate"` or `"frontgate"` -> `Camera` D1).
   - Invalid camera number or name raises `ValueError`.
5. **Non-Interactive Validation & Execution**:
   - Test `run_app` in `--non-interactive` mode missing `--date`: returns exit code 1 with error message.
   - Test `run_app` in `--non-interactive` mode missing `--camera`: returns exit code 1.
   - Test `run_app` in `--non-interactive` mode missing `--stream`: returns exit code 1.
   - Test `run_app` in `--non-interactive` mode with all valid arguments: completes successfully with mocked network calls.
6. **Cancellation & Signal Handling**:
   - Signal handler sets `cancel_event` and invokes `display_abort_notice`.
   - `run_app` interrupted via `KeyboardInterrupt` returns exit code 130 without tracebacks.
7. **CLI Formatters**:
   - `display_abort_notice()` outputs expected banner to stdout.
   - `display_error(msg)` outputs formatted error to stdout.

### 4.2 Static Checks & Test Suite
- Run `uv run pytest` to ensure 100% of existing and new tests pass.
- Run `uv run mypy src tests` to ensure strict typing compliance.
- Run `uv run ruff check .` to ensure formatting and linting compliance.
- Test console entrypoint invocation via `uv run hikvision-downloader --help`.

---

## 5. Invariant Checklist
- [x] Strict adherence to `.gemini/rules/1-workflow.md` (stopping at Step 5 for user approval).
- [x] Strict adherence to `.gemini/rules/2-security.md` (no hardcoded credentials, safe `.part` temp files).
- [x] Strict adherence to `.gemini/rules/3-design.md` (core decoupled from CLI/UI, clean separation of concerns).
- [x] Strict adherence to `.gemini/rules/4-coding-standards.md` (100% strict type annotations, zero bare exceptions, max line length <= 150).
- [x] Strict adherence to `.gemini/rules/6-skills.md` (only permitted CLI commands used).
