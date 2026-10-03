# Task 005: Headless CLI Engine, Graceful Interruption & Console Entry Point

## Objective
Build a robust command-line interface in `src/hikvision_downloader/cli/` that supports both headless flag-driven execution and interactive wizard fallback, complete with signal interruption handling (`Ctrl+C`), atomic `.part` cleanup on abort, clear help documentation, and a working PyPI console script entry point.

## Target Changes
1. **`src/hikvision_downloader/cli/app.py`**:
   - Implement argument parser supporting `--host`, `--date`, `--camera`, `--stream`, `--range`, `--output-dir`, and `--non-interactive`.
   - Add clear help documentation and epilog explaining how to abort execution (`Ctrl+C`).
   - If required parameters are missing and `--non-interactive` is not specified, seamlessly route to `cli/interactive.py`.
2. **Graceful Cancellation Handling**:
   - Register signal handlers for `SIGINT` (`Ctrl+C`) and handle `KeyboardInterrupt`.
   - Ensure the cancellation event is set immediately so `core/downloads.py` unlinks temporary `.part` files and exits cleanly without tracebacks.
3. **`src/hikvision_downloader/cli/formatters.py`**:
   - Add clean formatting helpers for download progress, speed, and abort notices.
4. **`pyproject.toml`**:
   - Update `[project.scripts]` to point `hikvision-downloader` to `hikvision_downloader.cli.app:main`.
5. **Tests (`tests/unit/test_cli.py`)**:
   - Add unit tests verifying argument parsing, default values, and help text formatting.

## Strict Invariants
- Adhere strictly to `.gemini/rules/1-workflow.md` and `.gemini/rules/4-coding-standards.md`.
- 100% type annotations on all parameters and return types across all new CLI files.
- Zero bare exceptions; no unhandled `KeyboardInterrupt` stack traces exposed to the user.
- Save Phase 1 plan to `.gemini/logs/task-005-plan.md` and stop for approval.
- Save Phase 2 walkthrough to `.gemini/logs/task-005-walkthrough.md`.