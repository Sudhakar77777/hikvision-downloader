import tomllib
from dataclasses import dataclass
from pathlib import Path

# ============================================================
# Camera configuration
# ============================================================


@dataclass(frozen=True)
class Camera:
    """Describe one configured camera and its NVR recording tracks."""

    number: int
    name: str
    ip_address: str
    main_track: int
    sub_track: int

    @property
    def display_name(self):
        """Return the camera name in the same format shown by the NVR UI."""

        return f"D{self.number} {self.name}"

    @property
    def archive_name(self):
        """Return the stable camera name used for output folders and files."""

        return f"D{self.number}_{self.name}"

    def stream_name(self, stream):
        """Return the human-readable stream name used for output paths."""

        if stream == "main":
            return "HD"

        if stream == "sub":
            return "SD"

        raise ValueError(f"Unknown stream: {stream}")

    def track_id(self, stream):
        """Return the NVR track ID for the requested stream."""

        if stream == "main":
            return self.main_track

        if stream == "sub":
            return self.sub_track

        raise ValueError(f"Unknown stream: {stream}")


# ============================================================
# User selection
# ============================================================


def load_cameras(config_file):
    """Load camera configuration from a TOML file."""

    path = Path(config_file)

    if not path.exists():
        raise FileNotFoundError(f"Camera configuration not found: {path}\nCopy config/cameras.example.toml to {path} and configure it.")

    with path.open("rb") as file:
        data = tomllib.load(file)

    cameras = {}

    for item in data.get("cameras", []):
        camera = Camera(
            number=item["number"],
            name=item["name"],
            ip_address=item["ip_address"],
            main_track=item["main_track"],
            sub_track=item["sub_track"],
        )

        cameras[camera.number] = camera

    return cameras


def display_camera_list(cameras):
    """Display available cameras."""

    print()
    print("Cameras")
    print("=" * 60)

    for number, camera in cameras.items():
        print(f"{number:>3}. [{number:>2}] {camera.name:<18} {camera.ip_address}")

    print("=" * 60)


def ask_camera(cameras):
    """Ask the user to select a camera."""

    display_camera_list(cameras)

    while True:
        value = input("Select camera (q to quit): ").strip()

        if value.lower() == "q":
            return None

        try:
            camera_number = int(value)

            if camera_number not in cameras:
                raise ValueError

            return cameras[camera_number]

        except ValueError:
            print(f"Please enter a camera number from 1 to {len(cameras)}.")


def ask_stream():
    """Ask the user to select main or sub stream."""

    print()
    print("Stream")
    print("=" * 30)
    print("1. Main")
    print("2. Sub")
    print("=" * 30)

    while True:
        value = input("Select stream (q to quit): ").strip().lower()

        if value == "q":
            return None

        if value == "1":
            return "main"

        if value == "2":
            return "sub"

        print("Please enter 1 for Main or 2 for Sub.")


def display_selection(camera, stream):
    """Display the selected camera and stream."""

    track_id = camera.track_id(stream)

    print()
    print(f"Camera:    [{camera.number}] {camera.name}")
    print(f"Camera IP: {camera.ip_address}")
    print(f"Stream:    {stream.capitalize()}")
    print(f"Track ID:  {track_id}")
