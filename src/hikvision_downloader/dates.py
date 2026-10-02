"""Legacy dates module re-exporting from core.dates and cli."""

from .cli.formatters import display_available_dates
from .cli.interactive import ask_recording_date
from .core.dates import (
    build_daily_distribution_xml,
    discover_available_dates,
    parse_daily_distribution,
    previous_month,
    search_month,
)
from .core.models import RecordingDate

__all__ = [
    "RecordingDate",
    "ask_recording_date",
    "build_daily_distribution_xml",
    "discover_available_dates",
    "display_available_dates",
    "parse_daily_distribution",
    "previous_month",
    "search_month",
]
