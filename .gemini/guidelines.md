# Agent Guidelines & Rules of Engagement

## 1. Operating Rules & Boundaries
- **Zero Git Automation:** Never run `git` commands (`commit`, `push`, `add`, `reset`, `checkout`, etc.). Version control is strictly managed by the human engineer.
- **No File Relocation:** Never create, delete, move, or rename files between `.gemini/tasks/` and `.gemini/tasks-done/`. Only the human operator moves completed tasks to `tasks-done/`.
- **Strict Scope Boundaries:** Modify only the files explicitly designated in the active task file. Never create speculative files, utility modules, or refactor unrelated code.
- **Human-in-the-Loop Completion:** When a task is complete, stop immediately. Output a structured summary of changes made, tests executed, and files touched. Wait for human review.

## 2. Security & Sanitization Guardrails
- **No Hardcoded Credentials:** Never write or leave passwords, API tokens, auth hashes, or session cookies in source code, configuration files, or documentation.
- **No Private Infrastructure Identifiers:** Never hardcode private IP addresses, internal camera URLs, or physical site names. Use RFC 5737 placeholders (`192.168.1.100`, `admin`, etc.).
- **Local Settings Isolation:** Keep sensitive values in `.env` (ignored by git). Document variables solely via `.env.example`.

## 3. Code Standards & Architecture
- **Single Responsibility Principle (SRP):** Keep modules focused on one clear domain (dates, recordings, download, auth, ui).
- **Core Decoupling:** Core logic inside `src/hikvision_downloader/core/` must never contain UI widgets, terminal UI tools, `input()`, or direct `print()` calls. Core functions return dataclasses, yield generators, or accept callback interfaces.
- **Type Safety & Typing:** All new functions and public methods must include Python type annotations (`typing` / built-in generics) and use `@dataclass` for structured payloads.
- **Formatting Conventions:** 
  - Maximum line length: 180 characters.
  - Pythonic naming (`snake_case` for functions/variables, `PascalCase` for classes).
- **Safe I/O:** Always use temporary `.part` files during downloads and verify stream completion before renaming. Skip pre-existing complete files.
- **Targeted Error Handling:** Do not use bare `except:` or `except Exception:` unless logging and re-raising. Catch specific exceptions (e.g., `requests.exceptions.Timeout`).

## 4. Testing & Verification Requirements
- All tests must use mocked responses or local fixtures. Never make live network calls against real NVR hardware in automated tests.