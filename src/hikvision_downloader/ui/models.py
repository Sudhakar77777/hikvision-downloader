"""Qt table models and data structures for the PySide6 Desktop GUI."""

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt
from PySide6.QtGui import QBrush, QColor

from ..core.models import Camera, CameraNumber, Recording, TrackId

_EMPTY_INDEX: QModelIndex = QModelIndex()


def format_size_human(bytes_count: int) -> str:
    """Format byte count into human-readable representation."""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    if bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    if bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.1f} MB"
    return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"


def format_iso_display(iso_str: str) -> str:
    """Format ISO timestamp (e.g., 2026-10-02T14:30:00Z) to readable format (YYYY-MM-DD HH:MM:SS)."""
    try:
        clean = iso_str.replace("Z", "").replace("T", " ")
        if "." in clean:
            clean = clean.split(".")[0]
        dt = datetime.fromisoformat(clean)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return str(iso_str)


def check_disk_space(
    output_dir: Path | str,
    required_bytes: int,
    safety_margin_mb: int = 100,
) -> tuple[bool, int, int]:
    """Check if target disk volume has sufficient free space including a safety margin.

    Returns:
        tuple of (has_sufficient_space: bool, required_bytes: int, free_bytes: int)
    """
    path = Path(output_dir)
    target = path if path.exists() else path.parent
    while not target.exists() and target.parent != target:
        target = target.parent

    try:
        usage = shutil.disk_usage(target if target.exists() else Path("."))
        free_bytes = usage.free
    except (OSError, ValueError):
        free_bytes = 0

    safety_buffer = safety_margin_mb * 1024 * 1024
    has_space = free_bytes >= (required_bytes + safety_buffer)
    return has_space, required_bytes, free_bytes


@dataclass
class CameraItem:
    """Represent one table row in the operator console camera selection view."""

    camera: Camera
    checked: bool = True

    @property
    def is_selected(self) -> bool:
        return self.checked

    @property
    def number(self) -> int:
        return int(self.camera.number)

    @property
    def display_name(self) -> str:
        """Return exact camera name as returned from NVR/ISAPI discovery without alteration."""
        return self.camera.name

    @property
    def model(self) -> str:
        return self.camera.model or ""


class CamerasTableModel(QAbstractTableModel):
    """Table model for discovered NVR cameras supporting checkboxes and sorting."""

    COL_CHECK: int = 0
    COL_NUM: int = 1
    COL_NAME: int = 2
    COL_MODEL: int = 3

    HEADERS: ClassVar[list[str]] = [
        "",
        "#",
        "Camera Name",
        "Hardware Model",
    ]

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[CameraItem] = []

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _EMPTY_INDEX) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = _EMPTY_INDEX) -> int:
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole and 0 <= section < len(self._items):
            return str(section + 1)
        return None

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        default_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == self.COL_CHECK:
            return default_flags | Qt.ItemFlag.ItemIsUserCheckable

        return default_flags

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item = self._items[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.CheckStateRole and col == self.COL_CHECK:
            return Qt.CheckState.Checked if item.checked else Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_NUM:
                return str(index.row() + 1)
            if col == self.COL_NAME:
                return item.display_name
            if col == self.COL_MODEL:
                return item.model

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (self.COL_CHECK, self.COL_NUM):
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == self.COL_NUM:
                return QBrush(QColor("#64748B"))
            if col == self.COL_MODEL:
                return QBrush(QColor("#94A3B8"))

        return None

    def setData(self, index: QModelIndex | QPersistentModelIndex, value: object, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return False

        item = self._items[index.row()]
        if index.column() == self.COL_CHECK and role == Qt.ItemDataRole.CheckStateRole:
            item.checked = value == Qt.CheckState.Checked or value is True or value == 2
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True

        return False

    def set_cameras(self, cameras: list[Camera] | dict[CameraNumber, Camera]) -> None:
        """Replace model contents with fresh camera items."""
        self.beginResetModel()
        cam_list: list[Camera] = list(cameras.values()) if isinstance(cameras, dict) else list(cameras)
        cam_list.sort(key=lambda c: int(c.number))
        self._items = [CameraItem(camera=c, checked=True) for c in cam_list]
        self.endResetModel()

    def clear(self) -> None:
        """Clear all camera items from model."""
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def select_all(self, checked: bool = True) -> None:
        """Set checked state for all camera items."""
        if not self._items:
            return
        for item in self._items:
            item.checked = checked
        top_left = self.index(0, self.COL_CHECK)
        bottom_right = self.index(len(self._items) - 1, self.COL_CHECK)
        self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.CheckStateRole])

    def get_selected_cameras(self) -> list[Camera]:
        """Return list of currently checked cameras."""
        return [item.camera for item in self._items if item.checked]

    def get_all_cameras(self) -> list[Camera]:
        """Return list of all cameras in model."""
        return [item.camera for item in self._items]

    def get_items(self) -> list[CameraItem]:
        """Return all CameraItem objects."""
        return list(self._items)

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """Sort rows by column."""
        if not self._items:
            return

        reverse = order == Qt.SortOrder.DescendingOrder
        self.beginResetModel()

        if column == self.COL_CHECK:
            self._items.sort(key=lambda x: x.checked, reverse=reverse)
        elif column == self.COL_NUM:
            self._items.sort(key=lambda x: int(x.camera.number), reverse=reverse)
        elif column == self.COL_NAME:
            self._items.sort(key=lambda x: (int(x.camera.number), x.camera.name), reverse=reverse)
        elif column == self.COL_MODEL:
            self._items.sort(key=lambda x: (x.camera.model or "", int(x.camera.number)), reverse=reverse)

        self.endResetModel()


@dataclass
class RecordingItem:
    """Represent one table row in the operator console recordings view."""

    recording: Recording
    camera: Camera
    stream: str
    track_id: TrackId
    checked: bool = True
    status: str = "Pending"
    error_message: str | None = None
    actual_bytes: int = 0

    @property
    def filename(self) -> str:
        return self.recording.name

    @property
    def size_bytes(self) -> int:
        return int(self.recording.size_bytes)


class RecordingsTableModel(QAbstractTableModel):
    """Table model for discovered NVR recording segments supporting checkboxes, row numbers, and sorting."""

    COL_CHECK: int = 0
    COL_NUM: int = 1
    COL_CAMERA: int = 2
    COL_STREAM: int = 3
    COL_FILENAME: int = 4
    COL_START: int = 5
    COL_END: int = 6
    COL_SIZE: int = 7
    COL_STATUS: int = 8

    HEADERS: ClassVar[list[str]] = [
        "",
        "#",
        "Camera",
        "Stream",
        "File Name",
        "Start Time",
        "End Time",
        "Size",
        "Status",
    ]

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[RecordingItem] = []

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _EMPTY_INDEX) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = _EMPTY_INDEX) -> int:
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole and 0 <= section < len(self._items):
            return str(section + 1)
        return None

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        default_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == self.COL_CHECK:
            return default_flags | Qt.ItemFlag.ItemIsUserCheckable

        return default_flags

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item = self._items[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.CheckStateRole and col == self.COL_CHECK:
            return Qt.CheckState.Checked if item.checked else Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_NUM:
                return str(index.row() + 1)
            if col == self.COL_CAMERA:
                return item.camera.name
            if col == self.COL_STREAM:
                return item.stream.upper()
            if col == self.COL_FILENAME:
                return item.filename
            if col == self.COL_START:
                return format_iso_display(str(item.recording.start))
            if col == self.COL_END:
                return format_iso_display(str(item.recording.end))
            if col == self.COL_SIZE:
                return format_size_human(item.size_bytes)
            if col == self.COL_STATUS:
                return item.status

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (self.COL_CHECK, self.COL_NUM, self.COL_STREAM, self.COL_STATUS):
                return int(Qt.AlignmentFlag.AlignCenter)
            if col == self.COL_SIZE:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == self.COL_NUM:
                return QBrush(QColor("#64748B"))
            if col == self.COL_STATUS:
                if item.status == "Completed":
                    return QBrush(QColor("#10B981"))
                if item.status == "Downloading" or item.status.startswith("Downloading"):
                    return QBrush(QColor("#38BDF8"))
                if item.status in ("Skipped", "Aborted", "Cancelled"):
                    return QBrush(QColor("#F59E0B"))
                if item.status == "Failed":
                    return QBrush(QColor("#EF4444"))
                return QBrush(QColor("#94A3B8"))
            if col == self.COL_STREAM:
                return QBrush(QColor("#F37021" if item.stream.upper() == "HD" else "#1E6B7B"))

        return None

    def setData(self, index: QModelIndex | QPersistentModelIndex, value: object, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return False

        item = self._items[index.row()]
        if index.column() == self.COL_CHECK and role == Qt.ItemDataRole.CheckStateRole:
            item.checked = value == Qt.CheckState.Checked or value is True or value == 2
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True

        return False

    def set_recordings(self, items: list[RecordingItem]) -> None:
        """Replace model contents with fresh recording items."""
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def clear(self) -> None:
        """Clear all recording items from model."""
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def select_all(self, checked: bool = True) -> None:
        """Set checked state for all recording items."""
        if not self._items:
            return
        for item in self._items:
            item.checked = checked
        top_left = self.index(0, self.COL_CHECK)
        bottom_right = self.index(len(self._items) - 1, self.COL_CHECK)
        self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.CheckStateRole])

    def select_range(self, start_idx: int, count: int) -> None:
        """Select a specific contiguous 1-based index range, deselecting others."""
        if not self._items:
            return
        total = len(self._items)
        for i, item in enumerate(self._items, start=1):
            item.checked = start_idx <= i < start_idx + count
        top_left = self.index(0, self.COL_CHECK)
        bottom_right = self.index(total - 1, self.COL_CHECK)
        self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.CheckStateRole])

    def get_selected_items(self) -> list[RecordingItem]:
        """Return list of currently checked recording items."""
        return [item for item in self._items if item.checked]

    def get_total_selected_size(self) -> int:
        """Return aggregate size in bytes of checked recording items."""
        return sum(item.size_bytes for item in self._items if item.checked)

    def get_total_count(self) -> int:
        """Return total count of recordings in model."""
        return len(self._items)

    def get_selected_count(self) -> int:
        """Return count of checked recordings."""
        return sum(1 for item in self._items if item.checked)

    def update_item_status(
        self,
        filename: str,
        status: str,
        error: str | None = None,
        bytes_downloaded: int = 0,
    ) -> None:
        """Update status for a specific recording file by name."""
        for row, item in enumerate(self._items):
            if item.filename == filename or filename.endswith(item.filename) or item.filename.endswith(filename):
                item.status = status
                if error:
                    item.error_message = error
                if bytes_downloaded > 0:
                    item.actual_bytes = bytes_downloaded
                idx = self.index(row, self.COL_STATUS)
                self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ForegroundRole])
                break

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """Sort rows by column."""
        if not self._items:
            return

        reverse = order == Qt.SortOrder.DescendingOrder
        self.beginResetModel()

        if column == self.COL_CHECK:
            self._items.sort(key=lambda x: x.checked, reverse=reverse)
        elif column == self.COL_NUM:
            self._items.sort(key=lambda x: (int(x.camera.number), str(x.recording.start)), reverse=reverse)
        elif column == self.COL_CAMERA:
            self._items.sort(key=lambda x: (int(x.camera.number), x.camera.name), reverse=reverse)
        elif column == self.COL_STREAM:
            self._items.sort(key=lambda x: x.stream, reverse=reverse)
        elif column == self.COL_FILENAME:
            self._items.sort(key=lambda x: x.filename, reverse=reverse)
        elif column == self.COL_START:
            self._items.sort(key=lambda x: str(x.recording.start), reverse=reverse)
        elif column == self.COL_END:
            self._items.sort(key=lambda x: str(x.recording.end), reverse=reverse)
        elif column == self.COL_SIZE:
            self._items.sort(key=lambda x: x.size_bytes, reverse=reverse)
        elif column == self.COL_STATUS:
            self._items.sort(key=lambda x: x.status, reverse=reverse)

        self.endResetModel()
