import csv
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

import requests

from ..http_client import request_with_retry
from .models import ByteCount, CameraNumber, ISODatetimeStr, Recording, TrackId


def build_search_xml(
    track_id: TrackId,
    start_time: str,
    end_time: str,
    position: int,
    batch_size: int = 1,
) -> str:
    """Build one Hikvision CMSearch request XML payload."""
    if int(track_id) < 1:
        raise ValueError(f"Invalid track ID: {track_id}")
    if position < 0:
        raise ValueError(f"Position cannot be negative: {position}")
    if batch_size < 1:
        raise ValueError(f"Batch size must be >= 1, got {batch_size}")

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
    <maxResults>{batch_size}</maxResults>
    <searchResultPostion>{position}</searchResultPostion>
    <metadataList>
        <metadataDescriptor>
            //recordType.meta.std-cgi.com
        </metadataDescriptor>
    </metadataList>
</CMSearchDescription>
"""


def get_query_value(url: str, key: str) -> str | None:
    """Safely extract a single query parameter value from a URL string."""
    query = parse_qs(urlparse(url).query)
    values = query.get(key)
    return values[0] if values else None


def parse_search_response(xml_text: str) -> list[Recording]:
    """Parse Hikvision CMSearchResult XML into validated Recording models."""
    if not xml_text or not xml_text.strip():
        return []

    root = ET.fromstring(xml_text)
    recordings: list[Recording] = []

    for item in root.iter():
        if not item.tag.endswith("searchMatchItem"):
            continue

        raw_start: str | None = None
        raw_end: str | None = None
        raw_uri: str | None = None

        for child in item.iter():
            tag = child.tag.split("}")[-1]

            if tag == "startTime" and child.text:
                raw_start = child.text.strip()
            elif tag == "endTime" and child.text:
                raw_end = child.text.strip()
            elif tag == "playbackURI" and child.text:
                raw_uri = child.text.strip()

        if not raw_uri or not raw_start or not raw_end:
            continue

        playback_uri = raw_uri.replace("&amp;", "&")
        name = get_query_value(playback_uri, "name") or "unknown"
        size_str = get_query_value(playback_uri, "size")

        try:
            size_int = int(size_str) if size_str else 0
        except ValueError:
            size_int = 0

        recordings.append(
            Recording(
                start=ISODatetimeStr(raw_start),
                end=ISODatetimeStr(raw_end),
                name=name,
                size_bytes=ByteCount(size_int),
                playback_uri=playback_uri,
            )
        )

    return recordings


def search_recordings(
    session: requests.Session,
    host: str,
    track_id: TrackId,
    recording_date: date,
    position: int,
    batch_size: int = 1,
    timeout: float = 120.0,
) -> list[Recording]:
    """Retrieve one pagination batch of recordings for a specified date and track."""
    start_time = f"{recording_date.isoformat()}T00:00:00Z"
    end_time = f"{recording_date.isoformat()}T23:59:59Z"

    url = f"http://{host}/ISAPI/ContentMgmt/search"

    try:
        response = request_with_retry(
            session,
            "POST",
            url,
            data=build_search_xml(track_id, start_time, end_time, position, batch_size=batch_size).encode("utf-8"),
            headers={
                "Content-Type": "application/xml",
            },
            timeout=timeout,
        )
        return parse_search_response(response.text)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 400:
            # NVR returns HTTP 400 Bad Request if the track ID is not a configured recording track
            return []
        raise



def get_all_recordings(
    session: requests.Session,
    host: str,
    track_id: TrackId,
    recording_date: date,
    batch_size: int = 1,
    timeout: float = 120.0,
) -> list[Recording]:
    """Retrieve the complete recording list for one date and track via pagination."""
    recordings: list[Recording] = []
    position = 0

    while True:
        batch = search_recordings(session, host, track_id, recording_date, position, batch_size=batch_size, timeout=timeout)

        if not batch:
            break

        recordings.extend(batch)

        if len(batch) < batch_size:
            break

        position += batch_size

    return recordings


def recording_total_size(recordings: Sequence[Recording]) -> ByteCount:
    """Calculate the total reported recording size in bytes across a sequence."""
    return ByteCount(sum(int(recording.size_bytes) for recording in recordings))


def save_recording_list(
    recordings: Sequence[Recording],
    output_dir: Path,
    camera_number: CameraNumber,
    camera_name: str,
    stream_name: str,
    recording_date: date,
) -> Path:
    """Save the recording list to CSV and return the resolved destination Path."""
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
                    int(recording.size_bytes),
                    recording.playback_uri,
                ]
            )

    return list_file
