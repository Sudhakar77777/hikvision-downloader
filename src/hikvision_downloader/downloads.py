"""Legacy downloads module re-exporting from core.downloads."""

from .core.downloads import (
    build_download_url,
    download_recording,
    download_recordings,
    download_recordings_concurrent,
    format_duration,
)

__all__ = [
    "build_download_url",
    "download_recording",
    "download_recordings",
    "download_recordings_concurrent",
    "format_duration",
]
