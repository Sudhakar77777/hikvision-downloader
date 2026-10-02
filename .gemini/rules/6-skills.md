# Skills & Tooling Guidelines

## 1. File Inspection & Manipulation
- **NEVER use shell commands for file inspection or edits:** Do NOT invoke `grep`, `egrep`, `sed`, `awk`, `cat`, `head`, `tail`, or `diff` via bash or terminal tool calls.
- **USE NATIVE AGENT TOOLS:** Use your IDE's native, permissionless file-system capabilities:
  - Use native **File Read** / **Read Range** tools to inspect files.
  - Use native **Workspace Search** / **Pattern Search** tools to locate strings or symbols across the codebase.
  - Use native **File Edit** / **Replace** tools for modifications.
- **Diff Presentation:** Present code comparisons directly within your markdown response using standard markdown diff blocks (````diff ... ````) rather than calling CLI `diff` utilities.

## 2. Permitted Terminal Commands
- The terminal tool should ONLY be used for test suite and environment commands:
  - `uv run pytest ...`
  - `uv run ruff ...`
  - `uv run mypy ...`
- Any other shell execution is forbidden unless explicitly requested by the user.