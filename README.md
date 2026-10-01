## Why This Project?

Hikvision NVRs provide a local web portal (typically accessed via `http://<NVR-IP>/doc/page/login.asp`) to configure settings and export footage over your local network. However, retrieving video through this native browser interface is notoriously unreliable:

* **Frequent Freezes & Hangs:** Browser-based transfers routinely stall or crash mid-stream.
* **Strict Concurrency Limits:** The web app restricts you to downloading only 2–3 files at a time.
* **Painful Manual Batching:** Exporting 100+ recordings from a single day requires clicking and babysitting every file individually.

---

### How It Works

This tool bypasses the fragile web UI to provide a direct, automated pipeline between your machine and the NVR over LAN:

1. **Local Authentication:** Connects directly to your NVR's endpoint using your credentials/session cookie. **TODO: Hardcoded currently**
2. **Interactive Querying:** Prompts you for the target date, camera channel, and timeframe, querying the NVR's internal database directly.
3. **Format & Stream Selection:** Lets you choose between HD (main stream) or SD (sub-stream) quality.
4. **Resilient Batch Download:** Pulls the complete list of matching files sequentially or concurrently straight to your local drive—without browser throttling or manual intervention.

# Hikvision Recording Downloader

 A small Python CLI for browsing and downloading recordings from a Hikvision NVR.

 The tool uses the Hikvision ISAPI interface to:

 - Discover which recent dates contain recordings.
- Let you choose a recording date.
- Select a camera and stream.
- Search recordings for that date.
- Display the available recording files.
- Download either a selected range or all files.
- Keep downloads organized by date, camera, and stream.
- Skip files that have already been downloaded.

 The project is intentionally split into small modules so the NVR interaction, date discovery, recording search, camera configuration, and downloading remain independently maintainable.

 ## How it works

```
                    ┌─────────────────────┐
                    │   Hikvision NVR     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Date Discovery     │
                    │                     │
                    │ Current month      │
                    │ Previous month     │
                    │ Previous-previous  │
                    │ (when applicable)  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Available Dates     │
                    │                     │
                    │ 2026-09             │
                    │ 01 02 03 ... 30     │
                    │                     │
                    │ 2026-08             │
                    │ 30 31               │
                    └──────────┬──────────┘
                               │
                         Select date
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Camera Selection    │
                    │                     │
                    │ D1 MainGate         │
                    │ D2 MainEntrance     │
                    │ D3 Office           │
                    │ ...                 │
                    └──────────┬──────────┘
                               │
                         Select stream
                               │
                         ┌─────┴─────┐
                         │           │
                        HD          SD
                         │           │
                         └─────┬─────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Recording Search    │
                    │                     │
                    │ NVR CMSearch API    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Recording List      │
                    │                     │
                    │ 1  start ... size  │
                    │ 2  start ... size  │
                    │ 3  start ... size  │
                    │ ...                 │
                    └──────────┬──────────┘
                               │
                       Select files
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Download            │
                    │                     │
                    │ Existing → skip     │
                    │ New → download      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Organized Archive   │
                    └─────────────────────┘
```

 ## Typical workflow

 The first question the application answers is:

 > **Which dates currently have recordings?**

 For example:

```
Available recording dates
=========================

2026-10
  01  02

2026-09
  01  02  03  04  05  06  07  08  09  10
  11  12  13  14  15  16  17  18  19  20
  21  22  23  24  25  26  27  28  29  30

2026-08
  30  31

Select date [YYYY-MM-DD]:
```

 Only days reported by the NVR as containing recordings are shown as available.

 The application checks the current month and previous month. If the previous month contains recordings, it also checks the month before that.

 This avoids unnecessarily querying older months when the NVR has already stopped retaining recordings.

 ## Camera and stream selection

 After selecting a date, the user selects a camera:

```
Cameras
=======================================================

  1. [D1] MainGate
  2. [D2] MainEntrance
  3. [D3] Office
  4. [D4] FirstFL
  ...
 11. [D11] TerraceFront

Select camera:
```

 Then the stream:

```
Stream
==============================

1. HD
2. SD

Select stream:
```

 Each camera has two recording tracks:

```
Camera 1 → HD / SD
Camera 2 → HD / SD
Camera 3 → HD / SD
...
```

 The application keeps the NVR-specific track IDs inside the camera configuration rather than exposing them as part of the user workflow.

 ## Recording search

 Once the date, camera, and stream are selected, the application searches the NVR for recordings for that specific day.

 The results are displayed before anything is downloaded:

```
====================================================================================================
   #  Start                 End                    Size (MB)  Name
====================================================================================================
   1  2026-09-15 00:00:00  2026-09-15 00:15:00       42.3  ...
   2  2026-09-15 00:15:00  2026-09-15 00:30:00       41.8  ...
   3  2026-09-15 00:30:00  2026-09-15 00:45:00       43.1  ...
====================================================================================================
Total: 96 recordings | 3.82 GB
```

 A CSV copy of the recording list is also saved alongside the downloaded files.

 ## Download selection

 The user can select a range of recordings.

 For example:

```
Enter: START COUNT

Examples:
  1 10   -> download files 1-10
  16 2   -> download files 16-17
  50 10  -> download files 50-59

Selection:
```

 This makes it possible to download only a portion of a day's recordings rather than downloading everything.

 Existing files are detected and skipped, so the downloader can safely be run again.

 ## Output structure

 Downloads are organized by:

```
date
  └── camera
       └── stream
```

 For example:

```
output/
└── 20260915_D4_FirstFL_HD/
    ├── 1_<recording>.mp4
    ├── 2_<recording>.mp4
    ├── 3_<recording>.mp4
    └── 20260915_D4_FirstFL_HD_recording-list.csv
```

 A different stream is kept separate:

```
output/
├── 20260915_D4_FirstFL_HD/
└── 20260915_D4_FirstFL_SD/
```

 This makes archives from multiple cameras, dates, and streams easy to distinguish.

 ## Project structure

 The application is split by responsibility:

```
src/
└── hikvision_downloader/
    ├── __init__.py
    ├── cameras.py
    ├── config.py
    ├── dates.py
    ├── downloads.py
    ├── http_client.py
    ├── recordings.py
    └── downloader.py
```

 ### `downloader.py`

 Application entry point and workflow orchestration.

 It coordinates:

```
Date discovery
      ↓
Date selection
      ↓
Camera selection
      ↓
Stream selection
      ↓
Recording search
      ↓
Recording selection
      ↓
Download
      ↓
Summary
```

 It deliberately contains very little NVR-specific implementation.

 ### `dates.py`

 Handles recording-date discovery.

 It communicates with the Hikvision daily-distribution API and converts the response into Python date objects.

 Responsibilities include:

 - Querying a month.
- Parsing `<record>true</record>`.
- Determining which recent months need to be queried.
- Displaying available dates.
- Validating the selected date.

 ### `cameras.py`

 Contains the camera configuration and camera/stream selection UI.

 A camera definition contains:

```
camera number
camera name
camera address
HD track
SD track
```

 The NVR-specific track mapping is kept here so the rest of the application can simply work with a camera and stream.

 ### `recordings.py`

 Handles recording searches and recording metadata.

 Responsibilities include:

 - Building CMSearch requests.
- Parsing search responses.
- Paging through recording results.
- Displaying recording lists.
- Saving recording metadata to CSV.
- Calculating total recording size.

 ### `downloads.py`

 Contains the actual download implementation.

 Responsibilities include:

 - Building Hikvision download URLs.
- Downloading individual recordings.
- Writing temporary `.part` files.
- Renaming completed downloads.
- Skipping existing files.
- Reporting download statistics.

 ### `http_client.py`

 Provides the common HTTP session and retry handling.

 This keeps authentication, request retries, timeouts, and HTTP error handling out of the application logic.

 ### `config.py`

 Loads application configuration and environment variables.

 Sensitive connection details belong here or in `.env`, not in source-controlled files.

 ## Installation

 The project uses Python and can be run with [`uv`](<https://docs.astral.sh/uv/>).

 Install the project:

```
uv sync
```

 ## Configuration

 Create a local `.env` file containing the credentials/session information required by your NVR.

 For example:

```
HIKVISION_HOST=<your-nvr-host>
HIKVISION_COOKIE=<your-session-cookie>
```

 Do **not** commit `.env` to the repository.

 A public repository should contain only a safe example configuration such as:

```
.env.example
```

 with placeholders rather than real infrastructure details or credentials.

 ## Running

 Run the application with:

```
uv run hikvision-downloader
```

 The interactive workflow then guides you through:

```
Available dates
      ↓
Select date
      ↓
Select camera
      ↓
Select stream
      ↓
Search recordings
      ↓
Select recordings
      ↓
Confirm
      ↓
Download
```

 ## Example

 Suppose the user wants recordings from September 15 from camera D4 using the HD stream.

 The workflow is approximately:

```
Select date [YYYY-MM-DD]: 2026-09-15

Select camera: 4

Stream
==============================
1. HD
2. SD

Select stream: 1
```

 The application searches the selected day's recordings and presents the available files.

 The user could then request:

```
Selection: 1 10
```

 which downloads the first ten recordings.

 The resulting archive would look similar to:

```
output/
└── 20260915_D4_FirstFL_HD/
    ├── 1_....mp4
    ├── 2_....mp4
    ├── ...
    ├── 10_....mp4
    └── 20260915_D4_FirstFL_HD_recording-list.csv
```

 ## Design goals

 The project intentionally follows a few simple principles:

 - **SRP** — each module has one clear responsibility.
- **DRY** — common HTTP, parsing, timing, and download behavior is centralized.
- **Explicit configuration** — camera and stream mappings are defined in one place.
- **Safe downloads** — incomplete files are written as `.part` files and existing completed files are skipped.
- **Small orchestration layer** — `downloader.py` coordinates the workflow instead of implementing every operation itself.
- **Human-readable output** — the CLI is designed for interactive use rather than being a thin wrapper around API calls.
- **No hardcoded infrastructure in documentation** — deployment-specific addresses and credentials stay local.

 ## Important note

 This project is designed for use with Hikvision NVR systems exposing the relevant ISAPI recording endpoints.
 Hikvision firmware versions and NVR configurations can differ, so endpoint behavior and available metadata may vary between systems.
