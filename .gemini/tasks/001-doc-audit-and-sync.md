# Task 001: Codebase Audit and Documentation Synchronization
<!-- INVARIANT: Adhere strictly to .gemini/rules/workflow.md. Generate Phase 1 Plan and wait for approval. -->

## Objective
Inspect `src/hikvision_downloader/` and synchronize `README.md` and `TODO.md` with the current ground-truth implementation.

## Target Files
- Inspect: `src/hikvision_downloader/*.py`
- Modify: `README.md`, `TODO.md`

## Instructions
1. Use native file-read tools (no shell grep/sed) to inspect all modules in `src/hikvision_downloader/` for current auth methods, endpoint paths, track structures, and data flows.
2. Formulate your Phase 1 Execution Plan detailing the discrepancies you found and your proposed surgical changes to `README.md` and `TODO.md`.
3. Stop and wait for user approval before modifying any files.