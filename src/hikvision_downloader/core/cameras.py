import tomllib
from pathlib import Path

from .models import Camera, CameraNumber, TrackId


def load_cameras(config_file: str | Path) -> dict[CameraNumber, Camera]:
    """Load and validate camera configurations from a TOML file."""
    path = Path(config_file)

    if not path.exists():
        raise FileNotFoundError(f"Camera configuration file not found: {path}\nCopy config/cameras.example.toml to {path} and configure it.")

    with path.open("rb") as file:
        data = tomllib.load(file)

    camera_entries = data.get("cameras")
    if not isinstance(camera_entries, list) or not camera_entries:
        raise ValueError(f"No valid [[cameras]] definitions found in configuration file: {path}")

    cameras: dict[CameraNumber, Camera] = {}
    seen_track_ids: set[TrackId] = set()

    for item in camera_entries:
        if not isinstance(item, dict):
            continue

        camera_number = CameraNumber(int(item["number"]))
        main_track = TrackId(int(item["main_track"]))
        sub_track = TrackId(int(item["sub_track"]))

        if camera_number in cameras:
            raise ValueError(f"Duplicate camera number '{camera_number}' found in configuration: {path}")

        if main_track in seen_track_ids:
            raise ValueError(f"Duplicate main track ID '{main_track}' assigned to camera {camera_number}")
        if sub_track in seen_track_ids:
            raise ValueError(f"Duplicate sub track ID '{sub_track}' assigned to camera {camera_number}")

        seen_track_ids.add(main_track)
        seen_track_ids.add(sub_track)

        camera = Camera(
            number=camera_number,
            name=str(item["name"]).strip(),
            ip_address=str(item["ip_address"]).strip(),
            main_track=main_track,
            sub_track=sub_track,
        )

        cameras[camera.number] = camera

    return cameras
