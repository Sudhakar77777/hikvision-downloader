# Task 004: Comprehensive Multi-Tier Testing Suite & Offline Fixtures

## Objective
Establish a clean, multi-directory test architecture (`tests/unit/`, `tests/functional/`, `tests/integration/`, `tests/fixtures/`) with high test coverage across all `core/` modules, ensuring offline tests execute with zero live network dependency.

## Target Changes
1. **`pyproject.toml`**:
   - Add `pytest>=8.0` and `pytest-mock>=3.14` to dev dependency group.
   - Configure `[tool.pytest.ini_options]` with test paths and an `integration` marker.
2. **`tests/fixtures/`**:
   - Create synthetic XML files for `dailyDistribution` and `CMSearchResult`.
3. **`tests/unit/`**:
   - `test_models.py`: Validate `Camera`, `RecordingDate`, `Recording`, `DownloadProgress`, `DownloadResult`.
   - `test_dates.py`: Validate `build_daily_distribution_xml`, `parse_daily_distribution`, `previous_month`.
   - `test_cameras.py`: Validate `load_cameras` with valid/invalid TOMLs.
   - `test_recordings.py`: Validate `build_search_xml`, `parse_search_response`, `save_recording_list`.
4. **`tests/functional/`**:
   - `test_download_engine.py`: Mocked HTTP chunk streaming, .part atomic rename, skipping existing files.
   - `test_cancellation.py`: Verify immediate download abort and .part cleanup on cancel event.
5. **`tests/integration/`**:
   - `test_live_nvr.py`: Live NVR hardware checks tagged with `@pytest.mark.integration` (auto-skipped if `.env` is absent).

## Strict Invariants
- Adhere strictly to `.gemini/rules/1-workflow.md` and `.gemini/rules/4-coding-standards.md`.
- 100% type annotations on all test functions and fixtures.
- All tests in `tests/unit/` and `tests/functional/` must pass completely offline.
- Save Phase 1 plan to `.gemini/logs/task-004-plan.md` and stop for approval.
- Save Phase 2 walkthrough to `.gemini/logs/task-004-walkthrough.md`.