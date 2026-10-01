import calendar
import time
from dataclasses import dataclass
from datetime import date

from .config import DATE_DISCOVERY_TRACK_ID, NVR_HOST, TIMEOUT
from .http_client import request_with_retry

# ============================================================
# Date discovery
# ============================================================


@dataclass(frozen=True)
class RecordingDate:
    """Represent one date known to contain recordings."""

    year: int
    month: int
    day: int

    @property
    def value(self):
        """Return the date as a standard Python date."""

        return date(self.year, self.month, self.day)

    @property
    def iso(self):
        """Return the date in YYYY-MM-DD format."""

        return self.value.isoformat()


def build_daily_distribution_xml(year, month):
    """Build a Hikvision trackDailyParam request."""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<trackDailyParam>
    <year>{year}</year>
    <monthOfYear>{month}</monthOfYear>
</trackDailyParam>
"""


def parse_daily_distribution(xml_text, year, month):
    """Parse Hikvision dailyDistribution XML and return recorded dates."""

    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_text)
    dates = []

    for day in root.iter():
        if not day.tag.endswith("day"):
            continue

        day_of_month = None
        has_recording = False

        for child in day:
            tag = child.tag.split("}")[-1]

            if tag == "dayOfMonth":
                day_of_month = int(child.text)

            elif tag == "record":
                has_recording = child.text.strip().lower() == "true"

        if has_recording and day_of_month is not None:
            dates.append(RecordingDate(year, month, day_of_month))

    return dates


def search_month(session, year, month):
    """Query one month of recording availability for the discovery track."""

    url = f"http://{NVR_HOST}/ISAPI/ContentMgmt/record/tracks/{DATE_DISCOVERY_TRACK_ID}/dailyDistribution"

    response = request_with_retry(
        session,
        "POST",
        url,
        data=build_daily_distribution_xml(year, month).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
        timeout=TIMEOUT,
    )

    return parse_daily_distribution(response.text, year, month)


def previous_month(year, month):
    """Return the previous calendar month."""

    if month == 1:
        return year - 1, 12

    return year, month - 1


def discover_available_dates(session, today=None):
    """Discover recent dates using current month, previous month, and conditionally one older month."""

    today = today or date.today()

    started = time.monotonic()

    current_year, current_month = today.year, today.month
    previous_year, previous_month_number = previous_month(current_year, current_month)

    available = {}

    current_dates = search_month(session, current_year, current_month)
    available[(current_year, current_month)] = current_dates

    previous_dates = search_month(session, previous_year, previous_month_number)
    available[(previous_year, previous_month_number)] = previous_dates

    if previous_dates:
        older_year, older_month = previous_month(previous_year, previous_month_number)
        older_dates = search_month(session, older_year, older_month)
        available[(older_year, older_month)] = older_dates

    duration = time.monotonic() - started

    return available, duration


def display_available_dates(months):
    """Display available recording dates grouped by month."""

    print()
    print("Available recording dates")
    print("=========================")

    for (year, month), dates in sorted(months.items(), reverse=True):
        recorded_days = sorted(item.day for item in dates)

        print()
        print(f"{year:04d}-{month:02d}")

        if not recorded_days:
            print("  No recordings")
            continue

        for start in range(0, len(recorded_days), 10):
            row = recorded_days[start : start + 10]
            print("  " + "  ".join(f"{day:02d}" for day in row))

    print()


def ask_recording_date(months):
    """Ask the user to select one of the discovered recording dates."""

    available_dates = {item.iso for dates in months.values() for item in dates}

    while True:
        value = input("Select date [YYYY-MM-DD] (q to quit): ").strip()

        if value.lower() == "q":
            return None

        try:
            selected = date.fromisoformat(value)

        except ValueError:
            print("Please enter a date in YYYY-MM-DD format.")
            continue

        if selected.isoformat() not in available_dates:
            print("No recording was reported for that date.")
            continue

        return selected
