# Task 002: Modularize Documentation (Requirements, Architecture, Roadmap)

## Objective
Decompose the monolithic and outdated `TODO.md` into three structured, long-term engineering documents under `docs/`, and remove `TODO.md` to prevent maintenance drift.

## Target Files
- Inspect: `TODO.md`, `README.md`, `src/hikvision_downloader/*.py`
- Create:
  - `docs/requirements.md`
  - `docs/architecture.md`
  - `docs/roadmap.md`
- Delete: `TODO.md` (upon Phase 3 approval)

## Scope of Work
1. **`docs/requirements.md`**:
   - Capture functional requirements (Date discovery, Camera/stream selection, Search, Range download, Skip existing files).
   - Capture non-functional requirements (Dual CLI and PySide6 desktop UI, cross-platform macOS/Windows, security without credentials in code, offline-friendly tests).
2. **`docs/architecture.md`**:
   - Detail the decoupled layers: Core services, CLI layer, PySide6 GUI layer.
   - Define data models (`Camera`, `RecordingSegment`, `DownloadProgress`).
   - Document non-blocking download patterns using callbacks/Qt signals.
3. **`docs/roadmap.md`**:
   - Establish sequential phases from current state to PyPI/Binary public release.
   - Map remaining TODO items into concrete task identifiers.
4. **Clean up `TODO.md`**:
   - Ensure all valuable context is transferred into the new docs before removing `TODO.md`.

## Lifecycle Invariants
- Adhere strictly to `.gemini/rules/1-workflow.md`.
- Save Phase 1 plan to `.gemini/logs/task-002-plan.md` and wait for approval.
- Save Phase 2 walkthrough to `.gemini/logs/task-002-walkthrough.md`.
- Stop for approval before deleting `TODO.md` or making any surgical updates.