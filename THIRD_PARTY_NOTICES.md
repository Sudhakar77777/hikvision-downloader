# Third-Party Software Notices and Disclosures

This project incorporates, depends on, or dynamically links with several open-source software libraries. This document outlines the relevant licenses, dynamic linking compliance notices, and attributions.

---

## 1. PySide6 / Qt Compliance Notice (GNU LGPLv3)

**`hikvision-downloader`** includes a desktop graphical user interface powered by **PySide6** (Qt 6 for Python), which is licensed under the **GNU Lesser General Public License version 3 (LGPLv3)**.

### Dynamic Linking & User Rights Disclosure:
- **Dynamic Linking:** `hikvision-downloader` interacts with PySide6 exclusively via dynamic runtime bindings and standard Python module imports without modifying any Qt or PySide6 shared object libraries (`.so`, `.dylib`, `.dll`).
- **Inspection & Substitution:** Under the terms of the LGPLv3, end users are fully entitled and empowered to inspect, re-link, or substitute modified or compatible versions of the Qt and PySide6 libraries within their execution environment (e.g., Python virtual environments or system packages).
- **Qt Source Code:** Upstream source code and licensing details for Qt and PySide6 are available at [https://code.qt.io/cgit/pyside/pyside-setup.git](https://code.qt.io/cgit/pyside/pyside-setup.git) and [https://www.qt.io/licensing/](https://www.qt.io/licensing/).

---

## 2. Third-Party Library Attributions

The following third-party dependencies are utilized within this project:

### Requests
- **License:** Apache License 2.0
- **Copyright:** (c) Kenneth Reitz / Requests Authors
- **Website:** [https://requests.readthedocs.io/](https://requests.readthedocs.io/)

### Keyring
- **License:** MIT License
- **Copyright:** (c) Jason R. Coombs, Kang Zhang
- **Website:** [https://github.com/jaraco/keyring](https://github.com/jaraco/keyring)

### Pydantic
- **License:** MIT License
- **Copyright:** (c) Samuel Colvin and Pydantic contributors
- **Website:** [https://github.com/pydantic/pydantic](https://github.com/pydantic/pydantic)

### Rich
- **License:** MIT License
- **Copyright:** (c) Will McGugan
- **Website:** [https://github.com/Textualize/rich](https://github.com/Textualize/rich)

### Pytest & Pytest-Mock
- **License:** MIT License
- **Copyright:** (c) Holger Krekel and pytest contributors; Bruno Oliveira
- **Website:** [https://pytest.org/](https://pytest.org/)

### Python-Dotenv
- **License:** BSD 3-Clause License
- **Copyright:** (c) Saurabh Kumar
- **Website:** [https://github.com/theskumar/python-dotenv](https://github.com/theskumar/python-dotenv)

### Ruff
- **License:** MIT License / Apache License 2.0
- **Copyright:** (c) Astral Software Inc.
- **Website:** [https://github.com/astral-sh/ruff](https://github.com/astral-sh/ruff)

### Mypy
- **License:** MIT License
- **Copyright:** (c) Jukka Lehtosalo and mypy contributors
- **Website:** [https://github.com/python/mypy](https://github.com/python/mypy)
