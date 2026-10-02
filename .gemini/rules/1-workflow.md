# Execution Workflow & Lifecycle

Every task MUST follow this strict step-by-step lifecycle. Never skip steps without explicit human approval. The agent must NEVER modify files in `.gemini/rules/`.

## Phase 1: Ingestion & Planning
1. Read all files under `.gemini/rules/` (`1-workflow.md`, `2-security.md`, `3-design.md`, `4-coding-standards.md`, `5-review-guidelines.md`, `6-skills.md`).
2. Read the assigned task file inside `.gemini/tasks/<task-id>-<name>.md`.
3. Create the plan document: `.gemini/logs/task-<task-id>-plan.md` containing:
   - Analysis of task requirements.
   - Target files to create, inspect, or modify.
   - Proposed logic and data structure changes.
   - Verification and testing plan.
4. Present the plan in chat.
5. **STOP AND WAIT FOR USER APPROVAL.** Do not edit, create, or delete code until approved.

## Phase 2: Implementation & Verification
6. Implement ONLY what was approved in the plan.
7. Run tests and static checks to confirm task completion and avoid regressions.
8. Create the walkthrough document: `.gemini/logs/task-<task-id>-walkthrough.md` containing:
   - What was implemented compared against the plan.
   - Verification results, test outputs, or CLI demonstrations.
   - Deviations or edge cases encountered.
9. Present the implementation walkthrough summary in chat.

## Phase 3: Documentation Review & Surgical Updates
10. Identify required documentation updates (`README.md`, `docs/requirements.md`, `docs/architecture.md`, `docs/roadmap.md`).
11. Propose surgical updates in chat (only what changed; no rewrites or extraneous edits).
12. **STOP AND WAIT FOR USER APPROVAL.** Apply documentation updates only after explicit approval.

## Phase 4: Task Completion & Archive
13. Verify `.gemini/logs/task-<task-id>-plan.md` and `.gemini/logs/task-<task-id>-walkthrough.md` exist and are complete.
14. The human operator verifies the work and moves the task file from `.gemini/tasks/<task-id>-<name>.md` to `.gemini/tasks-done/<task-id>-<name>.md`.
15. The agent must NEVER move task files automatically.