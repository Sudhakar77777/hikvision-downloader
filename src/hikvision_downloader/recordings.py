import csv
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

from .config import BATCH_SIZE, NVR_HOST, TIMEOUT
from .http_client import request_with_retry

# ============================================================
# Recording model
# ============================================================


@dataclass(frozen=True)
class Recording:
    """Represent one recording returned by Hikvision CMSearch."""

    start: str
    end: str
    name: str
    size: int
    playback_uri: str


# ============================================================
# Search
# ============================================================


def build_search_xml(track_id, start_time, end_time, position):
    """Build one Hikvision CMSearch request."""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<CMSearchDescription>
    <searchID>{{cbd5fc36-eb50-0001-c5a1-13931ff0d7a0}}</searchID>
    <trackList>
        <trackID>{track_id}</trackID>
    </trackList>
    <timeSpanList>
        <timeSpan>
            <startTime>{start_time}</startTime>
            <endTime>{end_time}</endTime>
        </timeSpan>
    </timeSpanList>
    <maxResults>{BATCH_SIZE}</maxResults>
    <searchResultPostion>{position}</searchResultPostion>
    <metadataList>
        <metadataDescriptor>
            //recordType.meta.std-cgi.com
        </metadataDescriptor>
    </metadataList>
</CMSearchDescription>
"""


def get_query_value(url, key):
    """Get one query-string value from a URL."""

    query = parse_qs(urlparse(url).query)
    values = query.get(key)

    return values[0] if values else None


def parse_search_response(xml_text):
    """Parse Hikvision CMSearchResult XML."""

    root = ET.fromstring(xml_text)
    recordings = []

    for item in root.iter():
        if not item.tag.endswith("searchMatchItem"):
            continue

        values = {
            "start": None,
            "end": None,
            "playback_uri": None,
        }

        for child in item.iter():
            tag = child.tag.split("}")[-1]

            if tag == "startTime":
                values["start"] = child.text

            elif tag == "endTime":
                values["end"] = child.text

            elif tag == "playbackURI":
                values["playback_uri"] = child.text

        if not values["playback_uri"]:
            continue

        playback_uri = values["playback_uri"].replace("&amp;", "&")

        name = get_query_value(playback_uri, "name")
        size = get_query_value(playback_uri, "size")

        recordings.append(
            Recording(
                start=values["start"],
                end=values["end"],
                name=name,
                size=int(size or 0),
                playback_uri=playback_uri,
            )
        )

    return recordings


def search_recordings(session, track_id, recording_date, position):
    """Retrieve one batch of recordings for a date and track."""

    start_time = f"{recording_date.isoformat()}T00:00:00Z"
    end_time = f"{recording_date.isoformat()}T23:59:59Z"

    url = f"http://{NVR_HOST}/ISAPI/ContentMgmt/search"

    response = request_with_retry(
        session,
        "POST",
        url,
        data=build_search_xml(track_id, start_time, end_time, position).encode("utf-8"),
        headers={
            "Content-Type": "application/xml",
        },
        timeout=TIMEOUT,
    )

    return parse_search_response(response.text)


def get_all_recordings(session, track_id, recording_date):
    """Retrieve the complete recording list for one date and track."""

    recordings = []
    position = 0

    while True:
        batch = search_recordings(session, track_id, recording_date, position)

        if not batch:
            break

        recordings.extend(batch)

        if len(batch) < BATCH_SIZE:
            break

        position += BATCH_SIZE

    return recordings


# ============================================================
# Recording list
# ============================================================


def recording_total_size(recordings):
    """Return the total reported recording size in bytes."""

    return sum(recording.size for recording in recordings)


def save_recording_list(recordings, output_dir, camera_number, camera_name, stream_name, recording_date):
    """Save the recording list to CSV."""

    output_dir.mkdir(parents=True, exist_ok=True)

    list_file = output_dir / f"{recording_date.isoformat()}_D{camera_number}_{camera_name}_{stream_name}_recording-list.csv"

    with open(list_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(
            [
                "number",
                "name",
                "start",
                "end",
                "size",
                "playback_uri",
            ]
        )

        for number, recording in enumerate(recordings, start=1):
            writer.writerow(
                [
                    number,
                    recording.name,
                    recording.start,
                    recording.end,
                    recording.size,
                    recording.playback_uri,
                ]
            )

    print(f"Recording list saved to: {list_file}")


def display_recording_list(recordings):
    """Display a compact numbered recording list."""

    print()
    print("=" * 110)
    print(f"{'#':>4}  {'Start':19}  {'End':19}  {'Size (MB)':>10}  Name")
    print("=" * 110)

    total_size = recording_total_size(recordings)

    for number, recording in enumerate(recordings, start=1):
        size_mb = recording.size / (1024 * 1024)

        print(f"{number:>4}  {recording.start[:19]}  {recording.end[:19]}  {size_mb:10.1f}  {recording.name}")

    print("=" * 110)
    print(f"Total: {len(recordings)} recordings  |  {total_size / (1024 * 1024 * 1024):.2f} GB")
    print()


def ask_download_selection(total):
    """Ask whether to download all files or a selected range."""

    print(f"Download all {total} files? [Y/n]")

    value = input().strip().lower()

    if value in ("", "y", "yes"):
        return 1, total

    if value not in ("n", "no"):
        print("Please answer yes or no.")
        return ask_download_selection(total)

    print()
    print("Enter: START COUNT")
    print("Examples:")
    print("  1 10   -> download files 1-10")
    print("  16 2   -> download files 16-17")
    print("  1 97   -> download files 1-97")
    print()

    while True:
        value = input("Selection (q to quit): ").strip()

        if value.lower() == "q":
            return None

        try:
            parts = value.split()

            if len(parts) != 2:
                raise ValueError

            start = int(parts[0])
            count = int(parts[1])

            if start < 1 or count < 1:
                raise ValueError

            end = start + count - 1

            if end > total:
                print(f"ERROR: last file would be {end}, but only {total} exist.")
                continue

            return start, count

        except ValueError:
            print("Please enter two numbers, for example: 1 10")
