from pathlib import Path

from dotenv import dotenv_values

# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
CAMERA_CONFIG = PROJECT_ROOT / "config" / "cameras.toml"

config = dotenv_values(ENV_FILE)

NVR_HOST = config.get("HIKVISION_HOST", "192.168.1.5")
COOKIE = config.get("HIKVISION_COOKIE")

if not COOKIE:
    raise RuntimeError(f"HIKVISION_COOKIE not found in {ENV_FILE}")

OUTPUT_ROOT = PROJECT_ROOT / "output"

DATE_DISCOVERY_TRACK_ID = 101

BATCH_SIZE = 1

TIMEOUT = 120
MAX_RETRIES = 3
RETRY_WAIT = 5

USER_AGENT = "HikvisionArchive/1.0"
