# Coding Standards

- **Language & Runtime:** Python 3.10+ managed via `uv`.
- **Typing:** Strict type annotations on all function signatures and public APIs.
- **Data Modeling:** Use `@dataclass` or `NamedTuple` for structured payloads (e.g., `Camera`, `RecordingSegment`, `DownloadProgress`).
- **Formatting Conventions:**
  - Maximum line length: 180 characters.
  - Standard Python naming: `snake_case` for functions/variables, `PascalCase` for classes.
- **Exception Handling:** Never use bare `except:`. Avoid generic `except Exception:` unless logging context and re-raising. Catch specific domain/network errors.