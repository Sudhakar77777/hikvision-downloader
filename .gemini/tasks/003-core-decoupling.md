# Task 003: Core Decoupling, Pydantic Domain Models & Strict Type Annotations

## Objective
Update project configuration to Python >=3.14 with Pydantic, decouple business logic into `src/hikvision_downloader/core/`, isolate terminal prompts and rendering into `src/hikvision_downloader/cli/`, and enforce 100% complete type annotations across all code in `src/`.

## Target Changes
1. **`pyproject.toml`**:
   - Update `requires-python = ">=3.14.0"`.
   - Add `pydantic>=2.0` to dependencies.
2. **Directory Restructuring**:
   - `src/hikvision_downloader/core/`:
     - `models.py` (Pydantic models and NewType semantic primitives).
     - `dates.py` (pure ISAPI date queries and parsing).
     - `cameras.py` (TOML configuration loading and camera mapping).
     - `recordings.py` (CMSearch XML generation, parsing, and pagination).
     - `downloads.py` (chunked streaming, atomic `.part` management, progress callbacks).
   - `src/hikvision_downloader/cli/`:
     - `interactive.py` (user input prompts and selection handlers).
     - `formatters.py` (ANSI tables and terminal rendering).
   - `src/hikvision_downloader/downloader.py` (thin CLI orchestrator).

## Strict Invariants
- Adhere strictly to `.gemini/rules/1-workflow.md` and `.gemini/rules/4-coding-standards.md`.
- Enforce 100% type annotations on every function, method, parameter, and return value in `src/`.
- No `print()`, `input()`, or terminal formatting inside `core/`.
- `downloads.py` must use a typed `ProgressCallback = Callable[[DownloadProgress], None]` and accept a `threading.Event` cancellation token.
- Save Phase 1 plan to `.gemini/logs/task-003-plan.md` and stop for approval.
- Save Phase 2 walkthrough to `.gemini/logs/task-003-walkthrough.md`.
- Ensure `uv run hikvision-downloader` functions with zero regressions.