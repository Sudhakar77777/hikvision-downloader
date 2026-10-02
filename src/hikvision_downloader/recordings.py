"""Legacy recordings module re-exporting from core.recordings and cli."""

from .cli.formatters import display_recording_list
from .cli.interactive import ask_download_selection
from .core.models import Recording
from .core.recordings import (
    build_search_xml,
    get_all_recordings,
    get_query_value,
    parse_search_response,
    recording_total_size,
    save_recording_list,
    search_recordings,
)

__all__ = [
    "Recording",
    "ask_download_selection",
    "build_search_xml",
    "display_recording_list",
    "get_all_recordings",
    "get_query_value",
    "parse_search_response",
    "recording_total_size",
    "save_recording_list",
    "search_recordings",
]
