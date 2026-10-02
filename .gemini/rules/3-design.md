# Design Guidelines

- **Single Responsibility Principle (SRP):** Each module must manage exactly one domain (HTTP client, date discovery, camera mapping, search, downloads, or UI).
- **Core Decoupling:** 
  - Modules inside `src/hikvision_downloader/core/` must NEVER import UI toolkits (`PySide6`, etc.) or rely on CLI I/O (`input()`, direct `print()`).
  - Core logic returns structured data (`dataclasses`), yields generators, or communicates through explicit callback protocols.
- **State Isolation:** Avoid global mutable state. Instantiate service clients with explicit configuration.