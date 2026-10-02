# Execution Workflow & Lifecycle

Every task MUST follow this strict step-by-step lifecycle. Never skip ahead without explicit human confirmation.

## Phase 1: Ingestion & Planning
1. Read all files under `.gemini/rules/` (`2-security.md`, `3-design.md`, `4-coding-standards.md`, `5-review-guidelines.md`, `6-skills.md`).
2. Read the assigned task file inside `.gemini/tasks/`.
3. Produce a structured **Execution Plan** in chat:
   - Analysis of task requirements.
   - Exact files to be created or edited.
   - Proposed logic and data structure changes.
   - Verification and testing plan.
4. **STOP AND WAIT FOR USER APPROVAL.** Do not edit or create code until approved.

## Phase 2: Implementation & Verification
5. Implement only what was approved in the plan.
6. Run tests and static checks to confirm the task is complete and regression-free.
7. Present an **Implementation Review**:
   - Compare what was actually implemented against the Phase 1 plan.
   - Highlight any deviations or edge cases encountered.

## Phase 3: Documentation Review & Surgical Updates
8. Identify if documentation (`README.md`, `docs/TODO.md`, designs, requirements) requires synchronization.
9. Propose **surgical updates** (only what changed; no rewrites or unnecessary reformatting).
10. **STOP AND WAIT FOR USER APPROVAL.** Apply documentation updates only after explicit approval.

## Phase 4: Task Completion & Archive
11. Present final validation status to the user.
12. Once the user signs off, move the active task from `.gemini/tasks/<task>.md` to `.gemini/tasks-done/<task>.md`.