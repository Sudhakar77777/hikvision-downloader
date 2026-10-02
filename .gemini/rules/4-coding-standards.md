# Coding Standards

- **Language & Runtime:** Python >=3.14 managed via `uv`.
- **100% Strict Type Annotations:** 
  - Every function, method, parameter, and return value across all code in `src/` must have explicit type annotations.
  - Zero bare/generic `Any` in domain code.
- **Domain Semantic Types:** Use `typing.NewType` for semantic primitives (`TrackId`, `CameraNumber`, `ByteCount`, `MegabitsPerSecond`, `ISODatetimeStr`) to prevent primitive obsession.
- **Data Modeling:** Use Pydantic models (`BaseModel` with strict validations or frozen configurations) for domain entities, configuration objects, and state payloads.
- **Formatting Conventions:**
  - Maximum line length: 150 characters (enforced via ruff).
  - Standard Python naming: `snake_case` for functions/variables, `PascalCase` for classes.
- **Exception Handling:** Never use bare `except:`. Avoid generic `except Exception:` unless logging context and re-raising. Catch specific domain/network errors.