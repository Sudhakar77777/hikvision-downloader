"""Legacy camera module re-exporting from core.cameras and cli."""

from .cli.formatters import display_camera_list, display_selection
from .cli.interactive import ask_camera, ask_stream
from .core.cameras import load_cameras
from .core.models import Camera

__all__ = [
    "Camera",
    "ask_camera",
    "ask_stream",
    "display_camera_list",
    "display_selection",
    "load_cameras",
]
