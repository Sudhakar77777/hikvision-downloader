import time
from datetime import UTC, date, datetime
from xml.etree import ElementTree as ET

import requests

from ..http_client import request_with_retry
from .models import RecordingDate, TrackId


def build_daily_distribution_xml(year: int, month: int) -> str:
    """Build a Hikvision trackDailyParam request XML string."""
    if not (2000 <= year <= 2100):
        raise ValueError(f"Year must be between 2000 and 2100, got {year}")
    if not (1 <= month <= 12):
        raise ValueError(f"Month must be between 1 and 12, got {month}")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<trackDailyParam>
    <year>{year}</year>
    <monthOfYear>{month}</monthOfYear>
</trackDailyParam>
"""


def parse_daily_distribution(xml_text: str, year: int, month: int) -> list[RecordingDate]:
    """Parse Hikvision dailyDistribution XML and return recorded dates."""
    if not xml_text or not xml_text.strip():
        return []

    root = ET.fromstring(xml_text)
    dates: list[RecordingDate] = []

    for day in root.iter():
        if not day.tag.endswith("day"):
            continue

        day_of_month: int | None = None
        has_recording: bool = False

        for child in day:
            tag = child.tag.split("}")[-1]

            if tag == "dayOfMonth" and child.text:
                try:
                    day_of_month = int(child.text.strip())
                except ValueError:
                    day_of_month = None

            elif tag == "record" and child.text:
                has_recording = child.text.strip().lower() == "true"

        if has_recording and day_of_month is not None:
            dates.append(RecordingDate(year=year, month=month, day=day_of_month))

    return sorted(dates, key=lambda d: d.day)


def search_month(
    session: requests.Session,
    host: str,
    track_id: TrackId,
    year: int,
    month: int,
    timeout: float = 120.0,
) -> list[RecordingDate]:
    """Query one month of recording availability for the discovery track."""
    if int(track_id) < 1:
        raise ValueError(f"Invalid track ID: {track_id}")

    url = f"http://{host}/ISAPI/ContentMgmt/record/tracks/{track_id}/dailyDistribution"

    response = request_with_retry(
        session,
        "POST",
        url,
        data=build_daily_distribution_xml(year, month).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
        timeout=timeout,
    )

    return parse_daily_distribution(response.text, year, month)


def previous_month(year: int, month: int) -> tuple[int, int]:
    """Return the previous calendar year and month tuple."""
    if month == 1:
        return year - 1, 12

    return year, month - 1


def discover_available_dates(
    session: requests.Session,
    host: str,
    discovery_track_id: TrackId,
    today: date | None = None,
    timeout: float = 120.0,
) -> tuple[dict[tuple[int, int], list[RecordingDate]], float]:
    """Discover recent dates using current month, previous month, and conditionally one older month."""
    today_date = today or datetime.now(UTC).date()

    started = time.monotonic()

    current_year, current_month = today_date.year, today_date.month
    previous_year, previous_month_number = previous_month(current_year, current_month)

    available: dict[tuple[int, int], list[RecordingDate]] = {}

    current_dates = search_month(session, host, discovery_track_id, current_year, current_month, timeout=timeout)
    available[(current_year, current_month)] = current_dates

    previous_dates = search_month(session, host, discovery_track_id, previous_year, previous_month_number, timeout=timeout)
    available[(previous_year, previous_month_number)] = previous_dates

    if previous_dates:
        older_year, older_month = previous_month(previous_year, previous_month_number)
        older_dates = search_month(session, host, discovery_track_id, older_year, older_month, timeout=timeout)
        available[(older_year, older_month)] = older_dates

    duration = time.monotonic() - started

    return available, duration
