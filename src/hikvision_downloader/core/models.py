from collections.abc import Callable
from datetime import date
from enum import StrEnum
from typing import NewType, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

# ============================================================
# Domain Semantic Primitives (Prevent Primitive Obsession)
# ============================================================

TrackId = NewType("TrackId", int)
CameraNumber = NewType("CameraNumber", int)
ByteCount = NewType("ByteCount", int)
MegabitsPerSecond = NewType("MegabitsPerSecond", float)
ISODatetimeStr = NewType("ISODatetimeStr", str)
NVRHost = NewType("NVRHost", str)

# ============================================================
# Stream Identifiers & Qualities
# ============================================================


class StreamType(StrEnum):
    """Internal stream identifier."""

    MAIN = "main"
    SUB = "sub"


class StreamQuality(StrEnum):
    """Human-readable display/archive stream descriptor."""

    HD = "HD"
    SD = "SD"


# ============================================================
# Domain Entity Models (Frozen Pydantic Models)
# ============================================================


class Camera(BaseModel):
    """Describe one configured camera and its NVR recording tracks."""

    model_config = ConfigDict(frozen=True)

    number: CameraNumber = Field(..., description="Camera channel number (>=1)")
    name: str = Field(..., min_length=1, description="Camera display name")
    ip_address: str = Field(..., min_length=1, description="Camera IP address or hostname")
    main_track: TrackId = Field(..., description="Main stream ISAPI track ID")
    sub_track: TrackId = Field(..., description="Sub stream ISAPI track ID")

    @model_validator(mode="after")
    def validate_camera_fields(self) -> Self:
        if int(self.number) < 1:
            raise ValueError(f"Camera number must be >= 1, got {self.number}")
        if int(self.main_track) < 1:
            raise ValueError(f"Main track ID must be >= 1, got {self.main_track}")
        if int(self.sub_track) < 1:
            raise ValueError(f"Sub track ID must be >= 1, got {self.sub_track}")
        return self

    @property
    def display_name(self) -> str:
        """Return formatted camera name matching NVR UI (e.g., 'D1 MainGate')."""
        return f"D{self.number} {self.name}"

    @property
    def archive_name(self) -> str:
        """Return sanitized folder-safe name (e.g., 'D1_MainGate')."""
        return f"D{self.number}_{self.name}"

    def stream_quality(self, stream: StreamType) -> StreamQuality:
        """Map stream type to user-facing quality enum."""
        if stream == StreamType.MAIN:
            return StreamQuality.HD
        if stream == StreamType.SUB:
            return StreamQuality.SD
        raise ValueError(f"Unknown stream type: {stream}")

    def stream_name(self, stream: StreamType) -> str:
        """Return string quality name ('HD' / 'SD') for backwards compatibility."""
        return self.stream_quality(stream).value

    def track_id(self, stream: StreamType) -> TrackId:
        """Return the NVR track ID for the specified stream type."""
        if stream == StreamType.MAIN:
            return self.main_track
        if stream == StreamType.SUB:
            return self.sub_track
        raise ValueError(f"Unknown stream type: {stream}")


class RecordingDate(BaseModel):
    """Represent one calendar date known to contain recordings."""

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2000, le=2100, description="Calendar year")
    month: int = Field(..., ge=1, le=12, description="Calendar month (1-12)")
    day: int = Field(..., ge=1, le=31, description="Day of month (1-31)")

    @model_validator(mode="after")
    def validate_calendar_date(self) -> Self:
        try:
            date(self.year, self.month, self.day)
        except ValueError as exc:
            raise ValueError(f"Invalid calendar date: {self.year}-{self.month:02d}-{self.day:02d}") from exc
        return self

    @property
    def value(self) -> date:
        """Return date as a standard Python date object."""
        return date(self.year, self.month, self.day)

    @property
    def iso(self) -> ISODatetimeStr:
        """Return date in YYYY-MM-DD ISO format."""
        return ISODatetimeStr(self.value.isoformat())


class Recording(BaseModel):
    """Represent one recording segment returned by Hikvision CMSearch."""

    model_config = ConfigDict(frozen=True)

    start: ISODatetimeStr = Field(..., min_length=1, description="Recording start ISO datetime")
    end: ISODatetimeStr = Field(..., min_length=1, description="Recording end ISO datetime")
    name: str = Field(..., min_length=1, description="Recording segment filename")
    size_bytes: ByteCount = Field(..., description="Reported segment size in bytes")
    playback_uri: str = Field(..., min_length=1, description="Playback RTSP URI")

    @model_validator(mode="after")
    def validate_recording_fields(self) -> Self:
        if int(self.size_bytes) < 0:
            raise ValueError(f"Recording size cannot be negative, got {self.size_bytes}")
        return self

    @property
    def size_mb(self) -> float:
        """Return segment size in Megabytes."""
        return float(self.size_bytes) / (1024 * 1024)

    @property
    def size(self) -> ByteCount:
        """Alias to size_bytes for convenience."""
        return self.size_bytes


class NVRAuthCredentials(BaseModel):
    """Encapsulate NVR credentials with secret masking."""

    model_config = ConfigDict(frozen=True)

    host: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: SecretStr
    port: int = Field(default=80, ge=1, le=65535)


class NVRConnectionProfile(BaseModel):
    """Stored connection profile metadata."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1)
    host: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    keyring_service: str = "hikvision_downloader"


class DownloadProgress(BaseModel):
    """Real-time progress notification emitted during file downloading."""

    model_config = ConfigDict(frozen=True)

    current_index: int = Field(..., ge=1, description="1-based index of current file in batch")
    total_files: int = Field(..., ge=1, description="Total files in the batch")
    filename: str = Field(..., min_length=1, description="Destination media filename")
    bytes_downloaded: ByteCount = Field(..., description="Total bytes downloaded for this file")
    file_size_bytes: ByteCount = Field(..., description="Target file size in bytes")
    speed_mbps: MegabitsPerSecond = Field(..., description="Instantaneous transfer speed in Mbps")
    elapsed_seconds: float = Field(..., ge=0.0, description="Elapsed time for current file in seconds")
    is_skipped: bool = Field(default=False, description="Whether the file was skipped because it already exists")

    @model_validator(mode="after")
    def validate_progress_fields(self) -> Self:
        if int(self.bytes_downloaded) < 0:
            raise ValueError(f"Bytes downloaded cannot be negative: {self.bytes_downloaded}")
        if int(self.file_size_bytes) < 0:
            raise ValueError(f"File size cannot be negative: {self.file_size_bytes}")
        if float(self.speed_mbps) < 0.0:
            raise ValueError(f"Speed cannot be negative: {self.speed_mbps}")
        return self


class DownloadResult(BaseModel):
    """Aggregate result summary after batch download completion."""

    model_config = ConfigDict(frozen=True)

    success: bool
    total_files: int = Field(..., ge=0)
    downloaded_files: int = Field(..., ge=0)
    skipped_files: int = Field(..., ge=0)
    downloaded_bytes: ByteCount = Field(..., description="Total bytes downloaded in batch")
    total_duration_seconds: float = Field(..., ge=0.0)
    failed_index: int | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_result_fields(self) -> Self:
        if int(self.downloaded_bytes) < 0:
            raise ValueError(f"Downloaded bytes cannot be negative: {self.downloaded_bytes}")
        return self


ProgressCallback = Callable[[DownloadProgress], None]
