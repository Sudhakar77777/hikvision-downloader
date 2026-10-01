# TODO

 Roadmap for making Hikvision Downloader a reusable, public, cross-platform application.

 ## 1\. Remove Hardcoded Camera Configuration

 **Status:** Open

 The current camera definitions are hardcoded in `cameras.py`, including:

 - Camera number
- Camera name
- Camera IP address
- Main stream track ID
- Sub stream track ID

 ### Goal

 Make camera configuration user-provided rather than tied to one particular NVR installation.

 Possible approaches to evaluate:

 - Import camera/channel information from the NVR.
- Discover available tracks through the Hikvision API.
- Allow users to configure cameras through the application.
- Persist configuration locally.

 The final application should not contain installation-specific camera names or IP addresses.

---

 ## 2\. Replace Hardcoded Session Cookie Login

 **Status:** Open

 The current application obtains `HIKVISION_COOKIE` from `.env`.

 This is useful during development but is not suitable for a public application.

 ### Goal

 Authenticate using:

```
NVR address
Username
Password
```

 and obtain the required Hikvision session automatically.

 Expected flow:

```
User
 │
 ├── NVR address
 ├── Username
 └── Password
        │
        ▼
   Hikvision login
        │
        ▼
   Session / cookie
        │
        ▼
   Authenticated API requests
```

 Do not require users to inspect browser cookies or manually copy a WebSession cookie.

 ### Security requirements

 - Never store the password in source code.
- Do not log passwords.
- Do not expose passwords in error messages.
- Avoid persisting credentials unless explicitly required.
- Prefer secure OS credential storage for persistent authentication.
- Keep session cookies in memory where practical.

 The existing `.env` cookie mechanism can remain useful as a temporary development/testing mechanism, but should not be the normal user-facing authentication flow.

---

 ## 3\. Build Desktop UI

 **Status:** Planned

 Build a native desktop UI using **PySide6 / Qt for Python**.

 PySide6 is the official Python binding for Qt and is available through Qt's Community Edition under LGPLv3/GPLv3 terms. Licensing requirements still need to be followed when distributing the application.  Qt Documentation+1

 ### Target platforms

 - macOS
- Windows

 Linux support can remain possible but is not a primary initial target.

 ### UI goals

 Replace the current interactive CLI workflow with a desktop workflow:

```
┌───────────────────────────────┐
│       Hikvision Archive       │
├───────────────────────────────┤
│                               │
│  Available recording dates    │
│                               │
│  2026-10                      │
│   01  02                      │
│                               │
│  2026-09                      │
│   01 02 03 04 ... 30         │
│                               │
│  Date:   [ 2026-09-15     ]   │
│  Camera: [ D4 FirstFL     ▼ ] │
│  Stream: [ HD             ▼ ] │
│                               │
│       [ Search Recordings ]   │
└───────────────────────────────┘
```

 After searching:

```
┌─────────────────────────────────────────────────┐
│ Recordings                                      │
├────┬──────────────┬──────────────┬──────────────┤
│ #  │ Start        │ End          │ Size         │
├────┼──────────────┼──────────────┼──────────────┤
│ ☑1 │ 00:00:00     │ 00:15:00     │ 182 MB       │
│ ☑2 │ 00:15:00     │ 00:30:00     │ 191 MB       │
│ ☐3 │ 00:30:00     │ 00:45:00     │ 177 MB       │
└────┴──────────────┴──────────────┴──────────────┘

             [ Download Selected ]
```

 ### UI requirements

 - Date availability display
- Camera selection
- Stream selection
- Recording search
- Recording table
- Select all / deselect all
- Download selected recordings
- Download progress
- Current file/status
- Overall progress
- Error reporting
- Cancel download
- Output directory selection
- NVR connection/login settings
- About / version information

---

 ## 4\. Keep Python Core Independent of the UI

 **Status:** Planned

 The existing downloader logic should remain reusable.

 The UI should call Python application services rather than duplicate Hikvision logic.

 Target architecture:

```
                 PySide6 UI
                     │
                     ▼
              Application Core
                     │
       ┌─────────────┼─────────────┐
       │             │             │
     Dates       Recordings     Downloads
       │             │             │
       └─────────────┼─────────────┘
                     │
                HTTP Client
                     │
                     ▼
                Hikvision NVR
```

 The core should not depend on:

 - `input()`
- terminal formatting
- `print()`
- GUI widgets

 The CLI can remain as an alternative interface while the GUI is developed.

---

 ## 5\. Clean Up Project Architecture

 **Status:** In Progress

 Keep responsibilities separated.

 Target structure:

```
src/
└── hikvision_downloader/
    ├── core/
    │   ├── cameras.py
    │   ├── dates.py
    │   ├── recordings.py
    │   ├── downloads.py
    │   └── http_client.py
    │
    ├── ui/
    │   ├── main_window.py
    │   ├── dates_view.py
    │   ├── recordings_view.py
    │   ├── settings_view.py
    │   └── widgets/
    │
    ├── cli/
    │   └── ...
    │
    └── app.py
```

 Follow:

 - SRP
- DRY
- Pythonic naming
- Small focused functions
- Type hints
- Dataclasses where appropriate
- No global mutable application state
- No unnecessary dependencies
- No duplicated Hikvision API logic

 Maintain the project's 180-character maximum line length convention.

---

 ## 6\. Recording Date Discovery

 **Status:** Implemented

 Current behavior:

 1. Query current month.
2. Query previous month.
3. If the previous month contains at least one recording day, query the month before it.
4. Stop there.

 Example:

```
Today: 2026-10-01

Query:
  2026-10
  2026-09

If September contains recordings:
  2026-08
```

 Do not blindly query every historical month.

 The NVR's `dailyDistribution` API is used to determine which days contain recordings.

```
record=true
       │
       ▼
recording exists for that day
```

---

 ## 7\. Camera / Stream Model

 **Status:** Partially Implemented

 The current track convention is:

```
101  → D1 MainGate       HD
102  → D1 MainGate       SD

201  → D2 MainEntrance   HD
202  → D2 MainEntrance   SD

301  → D3 Office         HD
302  → D3 Office         SD

...

1101 → D11 TerraceFront  HD
1102 → D11 TerraceFront  SD
```

 The application should expose meaningful stream names such as:

```
HD
SD
```

 rather than exposing implementation-specific track IDs to normal users.

 Track IDs should remain an internal NVR detail.

---

 ## 8\. Output Directory Convention

 **Status:** Implemented / Verify

 Downloads should be organized by date, camera and stream.

 Example:

```
output/
└── 20260915_D4_FirstFL_HD/
    ├── 1_recording.mp4
    ├── 2_recording.mp4
    └── 2026-09-15_D4_FirstFL_HD_recording-list.csv
```

 The track ID should not normally appear in user-facing directory or CSV names.

 Use:

```
HD
SD
```

 instead of:

```
401
402
```

 Track IDs remain internal implementation details.

---

 ## 9\. Public Repository Cleanup

 **Status:** Open

 Before making the repository public:

 ### Remove private information

 - NVR IP addresses
- Camera IP addresses
- Session cookies
- Usernames
- Passwords
- Browser cookies
- Installation-specific identifiers
- Private recording URLs
- Real recording metadata
- Generated output files

 ### Repository hygiene

 Add/update:

```
README.md
LICENSE
TODO.md
.gitignore
pyproject.toml
```

 Consider adding:

```
CONTRIBUTING.md
SECURITY.md
CHANGELOG.md
```

 only if they provide real value.

---

 ## 10\. Licensing

 **Status:** Open

 Choose and add an explicit license for the project.

 The repository's own license must be clearly separated from third-party dependency licenses.

 Current UI decision:

```
PySide6
   │
   └── Qt for Python Community Edition
          ├── LGPLv3
          └── GPLv3
```

 Qt documents that Qt for Python is available under LGPLv3/GPLv3 and commercial licensing, and also documents additional third-party licenses included in Qt for Python.  Qt Documentation+1

 Before the first public release:

 - Decide the project's own license.
- Review all Python dependencies.
- Record dependency licenses.
- Include required third-party notices.
- Review the exact PySide6/Qt modules being distributed.
- Avoid GPL-only Qt modules unless their licensing implications are intentionally accepted.

 Qt maintains a list of modules that are GPL-only in its open-source distribution, so this should be checked when choosing Qt components.  Qt Documentation

---

 ## 11\. Project Packaging

 **Status:** Open

 Make the project installable with modern Python packaging.

 Use:

```
pyproject.toml
```

 Keep the project compatible with:

```
uv
pip
venv
```

 PySide6 itself supports `pyproject.toml` integration through `pyside6-project`; current Qt documentation recommends the `pyproject.toml` format over the older `.pyproject` format.  Qt Documentation

 Example development workflow:

```
uv sync
uv run ...
```

---

 ## 12\. Desktop Application Packaging

 **Status:** Open

 Produce standalone applications for:

```
macOS
Windows
```

 Users should not need to install Python manually just to run the released desktop application.

 Evaluate PySide6 deployment options and choose a reproducible packaging workflow.

 Potential deliverables:

```
macOS
  .app
  .dmg

Windows
  .exe
  installer
```

 The Qt for Python documentation provides deployment guidance and tooling that should be evaluated before selecting the final packaging method.  Qt Documentation+1

---

 ## 13\. CI / GitHub Workflows

 **Status:** Open

 Add GitHub Actions for:

```
push
  │
  ├── lint
  ├── type checks
  ├── tests
  └── build
```

 Target:

```
macOS
Windows
```

 At minimum:

 - Install dependencies
- Run tests
- Run linting
- Run type checking
- Build/package the application
- Verify package contents

 Later:

```
tag v1.0.0
      │
      ▼
GitHub Release
      │
      ├── macOS artifact
      └── Windows artifact
```

---

 ## 14\. Testing

 **Status:** Open

 Add tests around the Hikvision-specific core before expanding the GUI.

 Priority areas:

 - Daily distribution XML parsing
- Date discovery logic
- Previous-month calculation
- Recording XML parsing
- Playback URI parsing
- Track selection
- HD/SD mapping
- Download URL construction
- Output path construction
- Existing-file detection
- Retry behavior
- Authentication failure handling

 Tests should not require access to a real NVR.

 Use saved XML/API fixtures.

---

 ## 15\. Error Handling

 **Status:** In Progress

 Avoid broad `except Exception` handlers where a narrower exception is appropriate.

 Handle expected failures explicitly:

```
Authentication failure
Connection failure
Timeout
Invalid XML
Invalid user input
HTTP errors
File-system errors
Download interruption
```

 GUI errors should be presented as useful messages rather than Python tracebacks.

 Unexpected exceptions should still be allowed to surface during development and should be logged appropriately in packaged applications.

---

 ## 16\. Logging

 **Status:** Open

 Replace ad-hoc diagnostic `print()` calls in the core with Python logging where appropriate.

 Requirements:

 - No passwords
- No session cookies
- No unnecessary sensitive URLs
- Useful connection/search/download diagnostics
- Different verbosity levels

 The GUI can expose relevant status information without exposing raw debug logs to normal users.

---

 ## 17\. User Configuration

 **Status:** Open

 Create a user-facing configuration mechanism for:

```
NVR address
Username
Authentication/session
Output directory
Download preferences
```

 Camera configuration should eventually be discovered from or configured against the user's own NVR rather than being embedded in the application source.

---

 ## 18\. Documentation

 **Status:** Partially Implemented

 Keep `README.md` intentionally concise.

 README should explain:

```
What it is
      ↓
How it works
      ↓
Application flow
      ↓
Example usage
      ↓
Development setup
      ↓
License
```

 Include diagrams and examples, but do not include:

 - Real NVR IP addresses
- Real camera IP addresses
- Cookies
- Private infrastructure details
- Installation-specific configuration

---

 ## 19\. No Docker

 **Status:** Decision Made

 Do **not** Dockerize the desktop application.

 This is a native desktop application intended to run on:

```
macOS
Windows
```

 Docker does not provide meaningful value for the primary user experience.

 Containerization may still be considered later for isolated development/testing services if a concrete need arises.

---

 ## 20\. Future Enhancements

 After the core desktop application is stable:

 - Remember recently used NVRs
- Secure credential storage
- Multiple NVR profiles
- Download queue
- Concurrent downloads
- Pause/resume
- Retry failed recordings
- Search/filter recordings
- Playback preview
- Disk-space indicator
- Automatic output organization
- Export recording metadata
- Application auto-update
- Localization

 These should remain secondary to the core workflow.

---

 # Target Application Flow

 The final application should follow this sequence:

```
                    START
                      │
                      ▼
              Connect / Login
                      │
                      ▼
          Discover recording dates
                      │
                      ▼
             Show available dates
                      │
                      ▼
             User selects date
                      │
                      ▼
             Select camera
                      │
                      ▼
             Select stream
                HD / SD
                      │
                      ▼
           Search NVR recordings
                      │
                      ▼
          Display recording list
                      │
                      ▼
            Select recordings
                      │
                      ▼
             Confirm download
                      │
                      ▼
                 Download
                      │
                      ▼
          Show progress / status
                      │
                      ▼
              Download complete
```

 The guiding principle is:

 > **Ask "Do we have recordings for that date?" first, then determine exactly what the user wants to retrieve.**

 That keeps the application's workflow aligned with how CCTV retrieval actually starts.

---

 # Current Technology Decision

```
Language       Python
Desktop UI     PySide6 / Qt 6
HTTP           requests
Packaging      pyproject.toml
Environment    uv
Target OS      macOS + Windows
Container      No
CI             GitHub Actions
```

 PySide6 provides the official Qt bindings for Python and includes both Qt Widgets and Qt Quick approaches; for this application, Qt Widgets are the initial UI direction because the application is primarily forms, selectors, tables, progress indicators, and desktop controls.  Qt Documentation+1

 ## Definition of Done for Public v1

 - [ ] No private IP addresses in repository
- [ ] No cookies or credentials in repository
- [ ] Camera discovery/configuration no longer hardcoded to one installation
- [ ] NVR username/password login implemented
- [ ] Session handling implemented securely
- [ ] PySide6 desktop UI implemented
- [ ] Python core separated from UI
- [ ] Date discovery working
- [ ] Camera/stream selection working
- [ ] Recording search working
- [ ] Download workflow working
- [ ] Output naming finalized
- [ ] Tests added
- [ ] Lint/type checks added
- [ ] GitHub Actions added
- [ ] macOS build tested
- [ ] Windows build tested
- [ ] License added
- [ ] Third-party notices reviewed
- [ ] README cleaned of private/install-specific information
- [ ] Release packaging documented
- [ ] No Docker dependency
