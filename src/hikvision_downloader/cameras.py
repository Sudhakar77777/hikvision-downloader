"""Legacy camera module re-exporting from core.cameras and cli."""

from .cli.formatters import display_camera_list, display_selection
from .cli.interactive import ask_camera, ask_stream
from .core.cameras import CameraDiscoveryService, discover_cameras_isapi, load_cameras
from .core.models import Camera

__all__ = [
    "Camera",
    "CameraDiscoveryService",
    "ask_camera",
    "ask_stream",
    "discover_cameras_isapi",
    "display_camera_list",
    "display_selection",
    "load_cameras",
]
