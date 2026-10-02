from pathlib import Path

from dotenv import dotenv_values

# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
ENV_FILE: Path = PROJECT_ROOT / ".env"
CAMERA_CONFIG: Path = PROJECT_ROOT / "config" / "cameras.toml"

config: dict[str, str | None] = dotenv_values(ENV_FILE)

NVR_HOST: str | None = config.get("HIKVISION_HOST")
COOKIE: str | None = config.get("HIKVISION_COOKIE")

OUTPUT_ROOT: Path = PROJECT_ROOT / "output"

DATE_DISCOVERY_TRACK_ID: int = 101


BATCH_SIZE: int = 50


TIMEOUT: float = 120.0
MAX_RETRIES: int = 3
RETRY_WAIT: float = 5.0

USER_AGENT: str = "HikvisionArchive/1.0"
