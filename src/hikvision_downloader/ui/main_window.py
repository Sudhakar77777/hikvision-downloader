"""Master Desktop GUI Application for Hikvision Downloader adhering to Arivedha design tokens."""

import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests
from PySide6.QtCore import QDate, QPoint, Qt
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QCursor,
    QFont,
    QFontDatabase,
    QIcon,
    QPixmap,
    QShowEvent,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    NVR_AUTH_TYPE,
    NVR_HOST,
    NVR_MAX_WORKERS,
    NVR_PASSWORD,
    NVR_PORT,
    NVR_USERNAME,
)
from ..core.models import (
    Camera,
    CameraNumber,
    DownloadProgress,
    DownloadResult,
    RecordingDate,
    TrackId,
)
from .keychain import (
    delete_nvr_password,
    get_nvr_credential,
    get_nvr_password,
    save_nvr_password,
)
from .models import (
    CameraItem,
    CamerasTableModel,
    RecordingItem,
    RecordingsTableModel,
    check_disk_space,
    format_size_human,
)
from .settings import (
    delete_profile_from_settings,
    get_saved_hosts_from_settings,
    get_saved_usernames_from_settings,
    load_profiles_from_settings,
    restore_window_geometry,
    save_profile_to_settings,
    save_window_geometry,
)
from .style import DARK_THEME_QSS, LIGHT_THEME_QSS
from .workers import AuthWorker, DatesWorker, DiscoveryWorker, DownloadWorker, SearchWorker

ASSETS_DIR: Path = Path(__file__).resolve().parent / "assets"
LOGO_SVG_PATH: Path = ASSETS_DIR / "logo.svg"
FAVICON_SVG_PATH: Path = ASSETS_DIR / "favicon.svg"
ARIVEDHA_LOGO_SVG_PATH: Path = ASSETS_DIR / "arivedha_logo.svg"


def resolve_default_output_dir() -> Path:
    """Resolve the default download output directory with priority for HIKVISION_OUTPUT_DIR."""
    env_dir = os.getenv("HIKVISION_OUTPUT_DIR")
    if env_dir and env_dir.strip():
        return Path(env_dir.strip()).expanduser().resolve()
    return (Path.home() / "Downloads" / "HikvisionArchive").resolve()


@dataclass
class WorkerActivity:
    """State of an active concurrent download worker."""

    worker_id: int
    filename: str = ""
    percent: int = 0
    speed_mb_s: float = 0.0
    active: bool = False


@dataclass
class WorkerRowWidgets:
    """UI widgets comprising a single concurrent download worker slot row."""

    container: QWidget
    prefix_label: QLabel
    progress_bar: QProgressBar
    detail_label: QLabel


class ProfileComboBox(QComboBox):
    """Editable QComboBox supporting dynamic popup refresh and profile selection."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._popup_callback: Callable[[], None] | None = None

    def set_popup_callback(self, callback: Callable[[], None]) -> None:
        """Set a callback to dynamically refresh items before showing the popup menu."""
        self._popup_callback = callback

    def showPopup(self) -> None:
        """Dynamically execute popup callback to load fresh items before displaying popup."""
        if self._popup_callback is not None:
            self._popup_callback()
        super().showPopup()

    def text(self) -> str:
        """Return trimmed current text."""
        return self.currentText().strip()

    def setText(self, text: str) -> None:
        """Set current text in the combo box editor."""
        self.setCurrentText(text)


class CameraRowWidget(QWidget):
    """Widget row for a camera inside the control panel list (legacy / utility)."""

    def __init__(self, camera: Camera, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.camera = camera
        self.setObjectName("cameraRow")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(6, 1, 6, 1)
        self._layout.setSpacing(6)

        # Real camera name without CH prefixes
        self.checkbox = QCheckBox(camera.name, self)
        self.checkbox.setChecked(True)
        self._layout.addWidget(self.checkbox, stretch=1)

        # Right Column: Model Badge if available
        if camera.model:
            model_label = QLabel(camera.model, self)
            model_label.setStyleSheet("font-size: 10px; color: #64748B; font-weight: 500; padding: 0 4px;")
            self._layout.addWidget(model_label)

    @property
    def is_selected(self) -> bool:
        return self.checkbox.isChecked()


class MainWindow(QMainWindow):
    """Master desktop application window orchestrating the operator console."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HikVision Downloader")

        # Initial sizing and centering
        screen_obj = QApplication.primaryScreen()
        if screen_obj is not None:
            screen = screen_obj.availableGeometry()
            width = max(1340, min(1600, int(screen.width() * 0.88)))
            height = max(920, min(1050, int(screen.height() * 0.88)))
            self.resize(width, height)
            self.move(screen.center() - self.rect().center())
        else:
            self.resize(1340, 920)
        self.setMinimumSize(1200, 820)
        restore_window_geometry(self)

        # Theme state
        self._is_dark_theme: bool = True

        # Apply programmatic system font to application
        app = QApplication.instance()
        if isinstance(app, QApplication):
            general_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
            app.setFont(general_font)

        # Apply application icon
        if FAVICON_SVG_PATH.exists():
            self.setWindowIcon(QIcon(str(FAVICON_SVG_PATH)))
        elif LOGO_SVG_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_SVG_PATH)))

        # Session & State
        self._session: requests.Session | None = None
        self._discovered_cameras: dict[CameraNumber, Camera] = {}
        self._discovered_dates: dict[tuple[int, int], list[RecordingDate]] = {}
        self._device_info: dict[str, str] = {}

        # Active Workers
        self._auth_worker: AuthWorker | None = None
        self._discovery_worker: DiscoveryWorker | None = None
        self._dates_worker: DatesWorker | None = None
        self._search_worker: SearchWorker | None = None
        self._download_worker: DownloadWorker | None = None

        # Concurrent Download Worker Tracking & Visual Multi-Worker Widgets
        self._worker_activities: dict[int, WorkerActivity] = {}
        self._worker_widgets: dict[int, WorkerRowWidgets] = {}
        self._file_to_worker: dict[str, int] = {}
        self._total_batch_files: int = 0
        self._total_batch_bytes: int = 0
        self._batch_start_time: float = 0.0

        # Table Models
        self._cameras_table_model = CamerasTableModel(self)
        self._table_model = RecordingsTableModel(self)
        self._table_model.dataChanged.connect(self._on_table_data_changed)
        self._table_model.modelReset.connect(self._on_table_data_changed)

        # Central Widget & Main Layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self._root_layout = QVBoxLayout(central_widget)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # Build UI Sections
        self._build_top_header()
        self._build_body_panels()
        self._build_footer_bar()

        # Load saved profiles, credentials and initial space check
        self._populate_profile_combos()
        self._load_initial_credentials()
        self._update_space_validation()

    # =========================================================================
    # UI Construction: Top Header Bar
    # =========================================================================

    def _build_top_header(self) -> None:
        header = QFrame(self)
        header.setObjectName("headerFrame")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 8, 12, 8)
        h_layout.setSpacing(10)
        h_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Brand / Logo
        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(10)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        logo_label = QLabel(self)
        if FAVICON_SVG_PATH.exists():
            pix = QPixmap(str(FAVICON_SVG_PATH)).scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pix)
        elif LOGO_SVG_PATH.exists():
            pix = QPixmap(str(LOGO_SVG_PATH)).scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pix)
        logo_label.setFixedSize(30, 30)
        brand_layout.addWidget(logo_label)

        title_label = QLabel("HikVision Downloader", self)
        title_label.setObjectName("appTitle")
        title_label.setStyleSheet("font-size: 15px; font-weight: 800; letter-spacing: 0.3px; border: none; background: transparent;")
        brand_layout.addWidget(title_label)
        h_layout.addLayout(brand_layout)

        h_layout.addSpacing(12)

        # Connection Form Inputs
        form_layout = QHBoxLayout()
        form_layout.setSpacing(8)
        form_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Host (Editable ComboBox populated from QSettings)
        form_layout.addWidget(QLabel("Host:", self))
        self.host_input = ProfileComboBox(self)
        self.host_input.set_popup_callback(self._refresh_host_dropdown_items)
        self.host_input.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.host_input.customContextMenuRequested.connect(self._show_credential_context_menu)
        host_line_edit = self.host_input.lineEdit()
        if host_line_edit is not None:
            host_line_edit.setPlaceholderText("192.168.1.100")
            host_line_edit.editingFinished.connect(lambda: self._auto_lookup_keychain(allow_user_autodiscovery=True))
            host_line_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            host_line_edit.customContextMenuRequested.connect(self._show_credential_context_menu)
        self.host_input.setMinimumWidth(130)
        self.host_input.setMaximumWidth(160)
        self.host_input.activated.connect(self._on_host_dropdown_selected)
        self.host_input.currentTextChanged.connect(self._on_host_combo_changed)
        form_layout.addWidget(self.host_input)

        # Port
        form_layout.addWidget(QLabel("Port:", self))
        self.port_input = QSpinBox(self)
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(NVR_PORT or 80)
        self.port_input.setFixedWidth(50)
        self.port_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.port_input.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.port_input.editingFinished.connect(lambda: self._auto_lookup_keychain(allow_user_autodiscovery=False))
        form_layout.addWidget(self.port_input)

        # Username (Editable ComboBox populated from QSettings)
        form_layout.addWidget(QLabel("User:", self))
        self.user_input = ProfileComboBox(self)
        self.user_input.set_popup_callback(self._refresh_user_dropdown_items)
        self.user_input.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.user_input.customContextMenuRequested.connect(self._show_credential_context_menu)
        user_line_edit = self.user_input.lineEdit()
        if user_line_edit is not None:
            user_line_edit.setPlaceholderText("admin")
            user_line_edit.editingFinished.connect(lambda: self._auto_lookup_keychain(allow_user_autodiscovery=False))
            user_line_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            user_line_edit.customContextMenuRequested.connect(self._show_credential_context_menu)
        self.user_input.setMinimumWidth(115)
        self.user_input.setMaximumWidth(140)
        self.user_input.activated.connect(self._on_user_dropdown_selected)
        self.user_input.currentTextChanged.connect(self._on_user_combo_changed)
        form_layout.addWidget(self.user_input)

        # Password
        form_layout.addWidget(QLabel("Password:", self))
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setMaximumWidth(100)
        form_layout.addWidget(self.password_input)

        # Remember in Keychain Checkbox
        self.remember_cb = QCheckBox("Save in Keychain", self)
        self.remember_cb.setChecked(True)
        form_layout.addWidget(self.remember_cb)

        form_layout.addSpacing(12)

        # Connect / Authenticate Button
        self.connect_btn = QPushButton("Connect", self)
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.setProperty("connected", "false")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        form_layout.addWidget(self.connect_btn)

        h_layout.addLayout(form_layout)
        h_layout.addStretch(1)

        # Status Badge Pill
        self.status_badge = QLabel("● Disconnected", self)
        self.status_badge.setObjectName("statusBadge")
        self.status_badge.setFixedHeight(28)
        self.status_badge.setStyleSheet(
            "background-color: #334155; color: #94A3B8; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
        )
        h_layout.addWidget(self.status_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Theme Switcher Button
        self.theme_btn = QPushButton("☀️", self)
        self.theme_btn.setObjectName("secondaryBtn")
        self.theme_btn.setFixedSize(36, 28)
        self.theme_btn.setToolTip("Toggle Light/Dark Theme")
        self.theme_btn.clicked.connect(self._toggle_theme)
        h_layout.addWidget(self.theme_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._root_layout.addWidget(header)

    # =========================================================================
    # UI Construction: Dedicated Footer Bar
    # =========================================================================

    def _build_footer_bar(self) -> None:
        footer = QFrame(self)
        footer.setObjectName("footerFrame")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(16, 6, 16, 6)
        f_layout.setSpacing(12)
        f_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(8)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        footer_icon = QLabel(self)
        logo_to_use = (
            ARIVEDHA_LOGO_SVG_PATH if ARIVEDHA_LOGO_SVG_PATH.exists() else (FAVICON_SVG_PATH if FAVICON_SVG_PATH.exists() else LOGO_SVG_PATH)
        )
        if logo_to_use.exists():
            pix = QPixmap(str(logo_to_use)).scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            footer_icon.setPixmap(pix)
        footer_icon.setFixedSize(18, 18)
        brand_layout.addWidget(footer_icon)

        footer_brand = QLabel("Product by Arivedha", self)
        footer_brand.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8; border: none; background: transparent;")
        brand_layout.addWidget(footer_brand)
        f_layout.addLayout(brand_layout)

        f_layout.addStretch(1)

        self.footer_device_label = QLabel("Disconnected · Ready", self)
        self.footer_device_label.setStyleSheet("font-size: 11px; color: #64748B; border: none; background: transparent;")
        f_layout.addWidget(self.footer_device_label)

        self._root_layout.addWidget(footer)

    # =========================================================================
    # UI Construction: Body Panels (Left Sidebar + Right Operation Area)
    # =========================================================================

    def _build_body_panels(self) -> None:
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.main_splitter.setObjectName("mainSplitter")

        # Left Operational Panel (Sources & Selection Only)
        self.left_panel = QWidget(self)
        self.left_panel.setMinimumWidth(410)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(14, 12, 8, 12)
        left_layout.setSpacing(12)

        # 1. Cameras & Streams Group
        left_layout.addWidget(self._build_camera_group(), stretch=1)

        # 2. Recording Time Window Group
        left_layout.addWidget(self._build_time_group())

        # 3. Pinned Search Button at bottom
        self.search_btn = QPushButton("🔍  SEARCH RECORDINGS", self)
        self.search_btn.setObjectName("searchBtn")
        self.search_btn.setEnabled(False)
        self.search_btn.clicked.connect(self._on_search_clicked)
        left_layout.addWidget(self.search_btn)

        self.main_splitter.addWidget(self.left_panel)

        # Right Operational Panel (Table, Download Settings, Actions & Logs)
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 12, 14, 12)
        right_layout.setSpacing(10)

        # Top: Segments Table
        right_layout.addWidget(self._build_recordings_view_panel(), stretch=6)

        # Middle: Download Settings Frame
        right_layout.addWidget(self._build_download_settings_panel())

        # Primary Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        self.start_download_btn = QPushButton("⬇  START BATCH DOWNLOAD", self)
        self.start_download_btn.setObjectName("downloadBtn")
        self.start_download_btn.setEnabled(False)
        self.start_download_btn.clicked.connect(self._on_start_download_clicked)
        action_bar.addWidget(self.start_download_btn, stretch=3)

        self.abort_btn = QPushButton("✕  CANCEL / ABORT", self)
        self.abort_btn.setObjectName("abortBtn")
        self.abort_btn.setEnabled(False)
        self.abort_btn.clicked.connect(self._on_abort_clicked)
        action_bar.addWidget(self.abort_btn, stretch=1)

        right_layout.addLayout(action_bar)

        # Bottom: Activity Log Console with integrated progress header
        right_layout.addWidget(self._build_console_log_panel(), stretch=4)

        self.main_splitter.addWidget(right_widget)
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([420, max(self.width() - 420, 750)])
        self._root_layout.addWidget(self.main_splitter, stretch=1)

    def _build_camera_group(self) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("cardFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Embedded Section Header
        header_label = QLabel("CAMERAS & STREAMS", self)
        header_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #38BDF8; background: transparent; border: none; padding-bottom: 6px;")
        layout.addWidget(header_label)

        # Quick Actions Bar
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        btn_select_all = QPushButton("Select All", self)
        btn_select_all.setObjectName("secondaryBtn")
        btn_select_all.clicked.connect(lambda: self._cameras_table_model.select_all(True))
        actions_layout.addWidget(btn_select_all)

        btn_deselect_all = QPushButton("Clear", self)
        btn_deselect_all.setObjectName("secondaryBtn")
        btn_deselect_all.clicked.connect(lambda: self._cameras_table_model.select_all(False))
        actions_layout.addWidget(btn_deselect_all)

        btn_refresh = QPushButton("Refresh Cameras", self)
        btn_refresh.setObjectName("secondaryBtn")
        btn_refresh.setMinimumWidth(110)
        btn_refresh.clicked.connect(self._on_refresh_cameras_clicked)
        actions_layout.addWidget(btn_refresh)

        layout.addLayout(actions_layout)

        # Stacked Widget for Camera Table vs Centered Empty Placeholder
        self.cameras_stack = QStackedWidget(self)

        # Page 0: Centered Placeholder Label
        placeholder_container = QWidget(self)
        p_layout = QVBoxLayout(placeholder_container)
        p_layout.setContentsMargins(12, 24, 12, 24)
        self.cameras_placeholder_label = QLabel("No cameras discovered. Click 'Connect' to discover cameras.", self)
        self.cameras_placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cameras_placeholder_label.setWordWrap(True)
        self.cameras_placeholder_label.setStyleSheet("color: #64748B; font-size: 12px; font-style: italic; padding: 20px;")
        p_layout.addWidget(self.cameras_placeholder_label)
        self.cameras_stack.addWidget(placeholder_container)

        # Page 1: Camera Table View
        self.cameras_table = QTableView(self)
        self.cameras_table.setObjectName("camerasTable")
        self.cameras_table.setModel(self._cameras_table_model)
        self.cameras_table.setSortingEnabled(True)
        self.cameras_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cameras_table.setAlternatingRowColors(True)
        self.cameras_table.setShowGrid(False)
        self.cameras_table.verticalHeader().setVisible(False)
        self.cameras_table.verticalHeader().setDefaultSectionSize(22)
        self.cameras_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.cameras_table.horizontalHeader().setStretchLastSection(True)

        self.cameras_table.setColumnWidth(CamerasTableModel.COL_CHECK, 28)
        self.cameras_table.setColumnWidth(CamerasTableModel.COL_NUM, 30)
        self.cameras_table.setColumnWidth(CamerasTableModel.COL_NAME, 170)
        self.cameras_table.setColumnWidth(CamerasTableModel.COL_MODEL, 130)
        self.cameras_table.horizontalHeader().setSectionResizeMode(CamerasTableModel.COL_CHECK, QHeaderView.ResizeMode.Fixed)
        self.cameras_table.horizontalHeader().setSectionResizeMode(CamerasTableModel.COL_NUM, QHeaderView.ResizeMode.Fixed)
        self.cameras_table.horizontalHeader().setSectionResizeMode(CamerasTableModel.COL_NAME, QHeaderView.ResizeMode.Stretch)

        self.cameras_stack.addWidget(self.cameras_table)
        self.cameras_stack.setCurrentIndex(0)

        layout.addWidget(self.cameras_stack, stretch=1)

        # Stream Quality Dropdown
        stream_row = QHBoxLayout()
        stream_row.setSpacing(8)
        stream_label = QLabel("Stream Quality:", self)
        stream_row.addWidget(stream_label)

        self.stream_combo = QComboBox(self)
        self.stream_combo.addItem("HD (Main Stream)", "HD")
        self.stream_combo.setEnabled(False)
        stream_row.addWidget(self.stream_combo, stretch=1)
        layout.addLayout(stream_row)

        return frame

    def _build_time_group(self) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("cardFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Embedded Section Header
        header_label = QLabel("RECORDING TIME WINDOW", self)
        header_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #38BDF8; background: transparent; border: none; padding-bottom: 6px;")
        layout.addWidget(header_label)

        # Row 1: Target Date Picker
        date_layout = QHBoxLayout()
        date_layout.setSpacing(8)
        date_layout.addWidget(QLabel("Date:", self))
        self.date_picker = QDateEdit(self)
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        date_layout.addWidget(self.date_picker, stretch=1)
        layout.addLayout(date_layout)

        # Row 2: 4 Preset Buttons
        presets_bar = QHBoxLayout()
        presets_bar.setSpacing(6)

        btn_am = QPushButton("AM (08-12)", self)
        btn_am.setObjectName("presetBtn")
        btn_am.clicked.connect(lambda: self._apply_time_preset("08", "00", "12", "00"))
        presets_bar.addWidget(btn_am)

        btn_noon = QPushButton("NOON (12-18)", self)
        btn_noon.setObjectName("presetBtn")
        btn_noon.clicked.connect(lambda: self._apply_time_preset("12", "00", "18", "00"))
        presets_bar.addWidget(btn_noon)

        btn_pm = QPushButton("PM (18-24)", self)
        btn_pm.setObjectName("presetBtn")
        btn_pm.clicked.connect(lambda: self._apply_time_preset("18", "00", "23", "59"))
        presets_bar.addWidget(btn_pm)

        btn_full = QPushButton("FULL (00-24)", self)
        btn_full.setObjectName("presetBtn")
        btn_full.clicked.connect(lambda: self._apply_time_preset("00", "00", "23", "59"))
        presets_bar.addWidget(btn_full)

        layout.addLayout(presets_bar)

        # Row 3: Symmetrical Time Range (From: [HH]:[MM]  To: [HH]:[MM])
        time_layout = QHBoxLayout()
        time_layout.setSpacing(4)
        time_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        time_layout.addWidget(QLabel("From:", self))
        self.start_hh_combo = QComboBox(self)
        self.start_hh_combo.addItems([f"{i:02d}" for i in range(24)])
        self.start_hh_combo.setCurrentText("00")
        self.start_hh_combo.setFixedWidth(56)
        time_layout.addWidget(self.start_hh_combo)

        lbl_col1 = QLabel(":", self)
        lbl_col1.setFixedWidth(10)
        lbl_col1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_layout.addWidget(lbl_col1)

        self.start_mm_combo = QComboBox(self)
        self.start_mm_combo.setEditable(True)
        self.start_mm_combo.addItems([f"{i:02d}" for i in range(0, 60, 5)])
        self.start_mm_combo.setCurrentText("00")
        self.start_mm_combo.setFixedWidth(56)
        time_layout.addWidget(self.start_mm_combo)

        time_layout.addSpacing(12)

        time_layout.addWidget(QLabel("To:", self))
        self.end_hh_combo = QComboBox(self)
        self.end_hh_combo.addItems([f"{i:02d}" for i in range(24)])
        self.end_hh_combo.setCurrentText("23")
        self.end_hh_combo.setFixedWidth(56)
        time_layout.addWidget(self.end_hh_combo)

        lbl_col2 = QLabel(":", self)
        lbl_col2.setFixedWidth(10)
        lbl_col2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_layout.addWidget(lbl_col2)

        self.end_mm_combo = QComboBox(self)
        self.end_mm_combo.setEditable(True)
        self.end_mm_combo.addItems([f"{i:02d}" for i in range(0, 60, 5)] + ["59"])
        self.end_mm_combo.setCurrentText("59")
        self.end_mm_combo.setFixedWidth(56)
        time_layout.addWidget(self.end_mm_combo)

        layout.addLayout(time_layout)

        return frame

    def _build_download_settings_panel(self) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("downloadSettingsFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # Section Header
        section_title = QLabel("DOWNLOAD SETTINGS", self)
        section_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #38BDF8; letter-spacing: 0.5px;")
        layout.addWidget(section_title)

        # Line 1: Output Directory + Browse ToolButton + Space Validation Pill
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(QLabel("Output Directory:", self))

        default_dir = resolve_default_output_dir()
        self.output_dir_input = QLineEdit(str(default_dir), self)
        self.output_dir_input.textChanged.connect(self._on_output_dir_changed)
        row1.addWidget(self.output_dir_input, stretch=1)

        self.browse_btn = QToolButton(self)
        self.browse_btn.setObjectName("browseBtn")
        self.browse_btn.setText("📂")
        self.browse_btn.setFixedSize(32, 26)
        self.browse_btn.setToolTip("Browse download directory")
        self.browse_btn.clicked.connect(self._on_browse_output_dir)
        row1.addWidget(self.browse_btn)

        self.space_label = QLabel("Disk: Checking...", self)
        self.space_label.setObjectName("spaceBadge")
        self.space_label.setStyleSheet("background-color: #064E3B; color: #10B981; font-weight: bold;")
        row1.addWidget(self.space_label)
        layout.addLayout(row1)

        # Line 2: Concurrent Workers + CSV Manifest Checkbox
        row2 = QHBoxLayout()
        row2.setSpacing(12)
        row2.addWidget(QLabel("Concurrent Workers:", self))

        self.worker_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.worker_slider.setRange(1, 4)
        self.worker_slider.setValue(NVR_MAX_WORKERS)
        self.worker_slider.setFixedWidth(100)
        self.worker_label = QLabel(f"{NVR_MAX_WORKERS} workers", self)
        self.worker_label.setStyleSheet("color: #38BDF8; font-weight: bold; min-width: 65px;")
        self.worker_slider.valueChanged.connect(lambda v: self.worker_label.setText(f"{v} worker{'s' if v > 1 else ''}"))
        row2.addWidget(self.worker_slider)
        row2.addWidget(self.worker_label)

        row2.addSpacing(16)
        self.csv_manifest_cb = QCheckBox("Generate recording-list.csv manifest", self)
        self.csv_manifest_cb.setChecked(True)
        row2.addWidget(self.csv_manifest_cb)
        row2.addStretch(1)
        layout.addLayout(row2)

        return frame

    def _build_recordings_view_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("cardFrame")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Top Bar: Section Title + Selection Actions
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        top_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        section_title = QLabel("RECORDINGS / VIDEO FILES", self)
        section_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #38BDF8; letter-spacing: 0.5px;")
        top_bar.addWidget(section_title)

        top_bar.addStretch(1)

        btn_all = QPushButton("Select All", self)
        btn_all.setObjectName("secondaryBtn")
        btn_all.setFixedHeight(24)
        btn_all.clicked.connect(lambda: self._table_model.select_all(True))
        top_bar.addWidget(btn_all)

        btn_none = QPushButton("Clear", self)
        btn_none.setObjectName("secondaryBtn")
        btn_none.setFixedHeight(24)
        btn_none.clicked.connect(lambda: self._table_model.select_all(False))
        top_bar.addWidget(btn_none)

        layout.addLayout(top_bar)

        # Table View
        self.table_view = QTableView(self)
        self.table_view.setModel(self._table_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setShowGrid(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(22)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)

        # Set specific column widths ensuring symmetry with left table
        self.table_view.setColumnWidth(RecordingsTableModel.COL_CHECK, 28)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_NUM, 30)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_CAMERA, 140)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_STREAM, 65)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_FILENAME, 220)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_START, 150)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_END, 150)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_SIZE, 90)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_STATUS, 100)

        self.table_view.horizontalHeader().setSectionResizeMode(RecordingsTableModel.COL_CHECK, QHeaderView.ResizeMode.Fixed)
        self.table_view.horizontalHeader().setSectionResizeMode(RecordingsTableModel.COL_NUM, QHeaderView.ResizeMode.Fixed)

        layout.addWidget(self.table_view)

        # Bottom Bar: Summary Segments Metric Badges below Table View
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)
        bottom_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Badge 1: Discovered Segments
        self.discovered_badge = QLabel("0 Segments Discovered · 0 B", self)
        self.discovered_badge.setObjectName("discoveredBadge")
        self.discovered_badge.setStyleSheet(
            "background-color: #1E293B; color: #E2E8F0; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; border: 1px solid #334155;"
        )
        bottom_bar.addWidget(self.discovered_badge)

        # Badge 2: Selected Segments
        self.selected_badge = QLabel("0 Selected · 0 B", self)
        self.selected_badge.setObjectName("selectedBadge")
        self.selected_badge.setStyleSheet(
            "background-color: #1E293B; color: #64748B; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; border: 1px solid #334155;"
        )
        bottom_bar.addWidget(self.selected_badge)

        bottom_bar.addStretch(1)
        layout.addLayout(bottom_bar)

        return panel

    def _build_console_log_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("cardFrame")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Tier 1: Header Line ([ LIVE CONSOLE ] ------------------- [ Clear ])
        tier1_header = QHBoxLayout()
        tier1_header.setSpacing(10)
        tier1_header.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        console_title = QLabel("LIVE CONSOLE", self)
        console_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #38BDF8; background: transparent; border: none;")
        tier1_header.addWidget(console_title)

        tier1_header.addStretch(1)

        clear_btn = QPushButton("Clear", self)
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.setFixedHeight(24)
        clear_btn.clicked.connect(self._on_clear_console)
        tier1_header.addWidget(clear_btn)

        layout.addLayout(tier1_header)

        # Tier 2: Dedicated Structured Worker Progress Panel
        progress_panel = QVBoxLayout()
        progress_panel.setSpacing(4)

        # Top Row: Overall Batch Progress Bar + Batch Summary Text
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.overall_progress_bar = QProgressBar(self)
        self.overall_progress_bar.setRange(0, 100)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setFixedHeight(8)
        self.overall_progress_bar.setTextVisible(False)
        top_row.addWidget(self.overall_progress_bar, stretch=1)

        self.progress_readout = QLabel("[  0% ]  Idle  |  0.0 Mbps  |  Elapsed: 00:00  |  ETA: --:--", self)
        self.progress_readout.setStyleSheet("font-size: 11px; color: #94A3B8; font-weight: 500;")
        top_row.addWidget(self.progress_readout)

        progress_panel.addLayout(top_row)

        # Worker Rows Container (up to 4 worker slot rows)
        self.worker_rows_container = QWidget(self)
        worker_layout = QVBoxLayout(self.worker_rows_container)
        worker_layout.setContentsMargins(0, 2, 0, 2)
        worker_layout.setSpacing(4)

        self._worker_widgets = {}
        for wid in range(1, 5):
            slot_widget = QWidget(self.worker_rows_container)
            slot_layout = QHBoxLayout(slot_widget)
            slot_layout.setContentsMargins(0, 0, 0, 0)
            slot_layout.setSpacing(8)
            slot_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            prefix_lbl = QLabel(f"Worker {wid}:", slot_widget)
            prefix_lbl.setFixedWidth(65)
            prefix_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #38BDF8;")
            slot_layout.addWidget(prefix_lbl)

            bar = QProgressBar(slot_widget)
            bar.setObjectName(f"workerBar{wid}")
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFixedHeight(6)
            bar.setFixedWidth(120)
            bar.setTextVisible(False)
            bar.setStyleSheet(
                "QProgressBar { background-color: #162032; border: 1px solid #334155; border-radius: 3px; height: 6px; }"
                "QProgressBar::chunk { background-color: #38BDF8; border-radius: 2px; }"
            )
            slot_layout.addWidget(bar)

            detail_lbl = QLabel("Idle", slot_widget)
            detail_lbl.setStyleSheet("font-size: 11px; color: #94A3B8; font-weight: 500;")
            slot_layout.addWidget(detail_lbl, stretch=1)

            self._worker_widgets[wid] = WorkerRowWidgets(
                container=slot_widget,
                prefix_label=prefix_lbl,
                progress_bar=bar,
                detail_label=detail_lbl,
            )
            worker_layout.addWidget(slot_widget)
            slot_widget.setVisible(False)

        self.worker_rows_container.setVisible(False)
        progress_panel.addWidget(self.worker_rows_container)

        layout.addLayout(progress_panel)

        # Tier 3: Terminal Console
        self.console_log = QPlainTextEdit(self)
        self.console_log.setObjectName("consoleLog")
        self.console_log.setReadOnly(True)
        self.console_log.setMaximumBlockCount(1000)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.console_log.setFont(fixed_font)
        layout.addWidget(self.console_log)

        return panel

    # =========================================================================
    # Theme Switching Logic
    # =========================================================================

    def _toggle_theme(self) -> None:
        self._is_dark_theme = not self._is_dark_theme
        app = QApplication.instance()
        if isinstance(app, QApplication):
            if self._is_dark_theme:
                app.setStyleSheet(DARK_THEME_QSS)
                self.theme_btn.setText("☀️")
            else:
                app.setStyleSheet(LIGHT_THEME_QSS)
                self.theme_btn.setText("🌙")

    # =========================================================================
    # Profiles & Keychain Logic
    # =========================================================================

    @property
    def summary_label(self) -> QLabel:
        """Backwards compatibility alias for summary label."""
        return self.discovered_badge

    def _refresh_host_dropdown_items(self) -> None:
        """Dynamically refresh the host dropdown list with latest items from QSettings before popup shows."""
        host_line_edit = self.host_input.lineEdit()
        current_text = host_line_edit.text() if host_line_edit is not None else self.host_input.currentText()
        hosts = get_saved_hosts_from_settings()
        if NVR_HOST and NVR_HOST not in hosts:
            hosts.insert(0, NVR_HOST)

        self.host_input.blockSignals(True)
        self.host_input.clear()
        for h in hosts:
            self.host_input.addItem(h)
        if host_line_edit is not None:
            host_line_edit.setText(current_text)
        else:
            self.host_input.setEditText(current_text)
        self.host_input.blockSignals(False)

    def _refresh_user_dropdown_items(self) -> None:
        """Dynamically refresh the user dropdown list with latest items from QSettings before popup shows."""
        user_line_edit = self.user_input.lineEdit()
        current_text = user_line_edit.text() if user_line_edit is not None else self.user_input.currentText()
        active_host = self.host_input.text()
        users = get_saved_usernames_from_settings(active_host) if active_host else get_saved_usernames_from_settings(None)
        default_user = NVR_USERNAME or "admin"
        if not users and default_user:
            users.append(default_user)

        self.user_input.blockSignals(True)
        self.user_input.clear()
        for u in users:
            self.user_input.addItem(u)
        if user_line_edit is not None:
            user_line_edit.setText(current_text)
        else:
            self.user_input.setEditText(current_text)
        self.user_input.blockSignals(False)

    def _on_host_dropdown_selected(self, index: int) -> None:
        """Handle user selecting a host profile from dropdown and immediately update credentials."""
        host = self.host_input.itemText(index) if index >= 0 else self.host_input.text()
        if host:
            profiles = load_profiles_from_settings()
            matching = [p for p in profiles if p.host.lower() == host.lower()]
            if matching:
                self.port_input.setValue(matching[0].port)
                users = get_saved_usernames_from_settings(host)
                if users:
                    self.user_input.blockSignals(True)
                    self.user_input.clear()
                    for u in users:
                        self.user_input.addItem(u)
                    chosen_user = matching[0].username or users[0]
                    self.user_input.setText(chosen_user)
                    self.user_input.blockSignals(False)
        self._auto_lookup_keychain(allow_user_autodiscovery=True)

    def _on_user_dropdown_selected(self, index: int) -> None:
        """Handle user selecting a username from dropdown and immediately query Keychain."""
        user = self.user_input.itemText(index) if index >= 0 else self.user_input.text()
        if user:
            self.user_input.setText(user)
        self._auto_lookup_keychain(allow_user_autodiscovery=False)

    def _populate_profile_combos(self, preserve_current: bool = True) -> None:
        """Populate Host and User combo boxes from saved QSettings."""
        current_h = self.host_input.text() if preserve_current else ""
        current_u = self.user_input.text() if preserve_current else ""

        hosts = get_saved_hosts_from_settings()
        if NVR_HOST and NVR_HOST not in hosts:
            hosts.insert(0, NVR_HOST)

        self.host_input.blockSignals(True)
        self.host_input.clear()
        for h in hosts:
            self.host_input.addItem(h)
        if current_h:
            self.host_input.setText(current_h)
        elif NVR_HOST:
            self.host_input.setText(NVR_HOST)
        elif hosts:
            self.host_input.setText(hosts[0])
        else:
            self.host_input.setEditText("")
        self.host_input.blockSignals(False)

        active_host = self.host_input.text()
        users = get_saved_usernames_from_settings(active_host) if active_host else []
        default_user = NVR_USERNAME or "admin"
        if not users and default_user:
            users.append(default_user)

        self.user_input.blockSignals(True)
        self.user_input.clear()
        for u in users:
            self.user_input.addItem(u)
        if current_u:
            self.user_input.setText(current_u)
        elif users:
            self.user_input.setText(users[0])
        else:
            self.user_input.setEditText("")
        self.user_input.blockSignals(False)

    def _on_host_combo_changed(self, host_text: str) -> None:
        """Update usernames dropdown and query keychain when host changes."""
        clean_host = host_text.strip()
        if clean_host:
            profiles = load_profiles_from_settings()
            matching = [p for p in profiles if p.host.lower() == clean_host.lower()]
            if matching:
                self.port_input.setValue(matching[0].port)
                users = get_saved_usernames_from_settings(clean_host)
                if users:
                    self.user_input.blockSignals(True)
                    self.user_input.clear()
                    for u in users:
                        self.user_input.addItem(u)
                    self.user_input.setText(users[0])
                    self.user_input.blockSignals(False)
        self._auto_lookup_keychain(allow_user_autodiscovery=True)

    def _on_user_combo_changed(self, user_text: str) -> None:
        """Query keychain when username changes without mutating username."""
        self._auto_lookup_keychain(allow_user_autodiscovery=False)

    def _load_initial_credentials(self) -> None:
        """Load initial credentials on startup."""
        host = self.host_input.text()
        user = self.user_input.text()
        port = self.port_input.value()

        if host:
            try:
                cred = get_nvr_credential(host, user, port) if user else get_nvr_credential(host, "", port)
                if cred is not None:
                    matched_user, password = cred
                    if matched_user and matched_user != user:
                        self.user_input.setText(matched_user)
                    self.password_input.setText(password)
                    self.remember_cb.setChecked(True)
                    self.password_input.setToolTip("🔑 Retrieved from OS Keychain")
                    self.log_message("INFO", f"Loaded password from OS Keychain for {matched_user or user}@{host}:{port}.")
                    return
            except (OSError, RuntimeError, ValueError) as exc:
                self.log_message("ERROR", f"OS Keychain access failed: {exc}")

        if NVR_PASSWORD:
            self.password_input.setText(NVR_PASSWORD)

    def _auto_lookup_keychain(self, allow_user_autodiscovery: bool = False) -> None:
        """Reactively lookup credentials from OS Keychain on host/user/port field edit."""
        host = self.host_input.text()
        user = self.user_input.text()
        port = self.port_input.value()

        if not host:
            return

        try:
            if user:
                password = get_nvr_password(host, user, port)
                if password is not None:
                    self.password_input.setText(password)
                    self.remember_cb.setChecked(True)
                    self.password_input.setToolTip("🔑 Retrieved from OS Keychain")
                    self.log_message("INFO", f"Loaded password from OS Keychain for {user}@{host}:{port}.")
                else:
                    self.password_input.clear()
                    self.password_input.setToolTip("")
                    self.log_message("DEBUG", f"No keychain password entry found for {user}@{host}:{port}.")
            elif allow_user_autodiscovery:
                # Fallback to credential auto-discovery across matching host ONLY when explicitly permitted
                cred = get_nvr_credential(host, "", port)
                if cred is not None:
                    matched_user, matched_pw = cred
                    if matched_user:
                        self.user_input.blockSignals(True)
                        self.user_input.setText(matched_user)
                        self.user_input.blockSignals(False)
                    self.password_input.setText(matched_pw)
                    self.remember_cb.setChecked(True)
                    self.password_input.setToolTip("🔑 Retrieved from OS Keychain")
                    self.log_message("INFO", f"Loaded password from OS Keychain for {matched_user}@{host}:{port}.")
                else:
                    self.password_input.clear()
                    self.password_input.setToolTip("")
            else:
                self.password_input.clear()
                self.password_input.setToolTip("")
        except (OSError, RuntimeError, ValueError) as exc:
            self.log_message("ERROR", f"OS Keychain access failed: {exc}")

    def _remove_current_profile_and_credentials(self) -> None:
        """Remove current profile and credentials from OS Keychain and QSettings."""
        host = self.host_input.text()
        user = self.user_input.text()
        port = self.port_input.value()
        if host:
            delete_nvr_password(host, user, port)
            delete_profile_from_settings(host, port, user)
            self.password_input.clear()
            self.password_input.setToolTip("")
            self.user_input.blockSignals(True)
            self.user_input.clear()
            self.user_input.setEditText("")
            self.user_input.blockSignals(False)
            self._populate_profile_combos(preserve_current=False)
            self.log_message("INFO", f"Removed stored profile & Keychain credentials for {user or 'host'}@{host}:{port}.")

    def _show_credential_context_menu(self, pos: QPoint | None = None) -> None:
        """Show context menu for removing stored profile and OS Keychain credentials."""
        menu = QMenu(self)
        delete_action = menu.addAction("Remove Stored Profile & Keychain Credentials")
        chosen = menu.exec(QCursor.pos())
        if chosen == delete_action:
            self._remove_current_profile_and_credentials()

    def _on_connection_field_changed(self) -> None:
        """Backwards-compatible alias for reactive keychain lookup."""
        self._auto_lookup_keychain()

    def _save_credentials_if_checked(self) -> None:
        """Persist successful connection profile in QSettings and save password in OS Keychain if requested."""
        host = self.host_input.text()
        user = self.user_input.text()
        port = self.port_input.value()
        password = self.password_input.text()

        if host and user:
            save_profile_to_settings(host, port, user)

        if self.remember_cb.isChecked() and host and user and password:
            try:
                if save_nvr_password(host, user, password, port):
                    self.log_message("INFO", f"Saved password in OS Keychain for {user}@{host}:{port}.")
                else:
                    self.log_message("ERROR", f"OS Keychain access failed: Could not persist credentials for {user}@{host}:{port}")
            except (OSError, RuntimeError, ValueError) as exc:
                self.log_message("ERROR", f"OS Keychain access failed: {exc}")
        elif not self.remember_cb.isChecked() and host and user:
            try:
                delete_nvr_password(host, user, port)
            except (OSError, RuntimeError, ValueError) as exc:
                self.log_message("ERROR", f"OS Keychain access failed: {exc}")

    # =========================================================================
    # Logging & Console Output
    # =========================================================================

    def log_message(self, level: str, message: str) -> None:
        """Append a timestamped log line to the live activity console."""
        timestamp = time.strftime("%H:%M:%S")
        color_map = {
            "DEBUG": "#64748B",
            "INFO": "#38BDF8",
            "SUCCESS": "#4ADE80",
            "WARN": "#F59E0B",
            "ERROR": "#EF4444",
            "SKIP": "#EAB308",
            "DOWNLOAD": "#F37021",
        }
        color = color_map.get(level.upper(), "#94A3B8")
        line = (
            f"<span style='color: #94A3B8;'>[{timestamp}]</span> "
            f"<span style='color: {color}; font-weight: bold;'>[{level.upper()}]</span> "
            f"<span style='color: #E2E8F0;'>{message}</span>"
        )
        self.console_log.appendHtml(line)
        self.console_log.verticalScrollBar().setValue(self.console_log.verticalScrollBar().maximum())

    def _on_clear_console(self) -> None:
        self.console_log.clear()

    # =========================================================================
    # Event Handlers: Connection, Discovery & Dates
    # =========================================================================

    def _on_connect_clicked(self) -> None:
        if self._session is not None:
            self._disconnect_session()
            return

        host = self.host_input.text()
        port = self.port_input.value()
        username = self.user_input.text()
        password = self.password_input.text()

        if not host:
            QMessageBox.warning(self, "Missing Host", "Please enter the NVR Host IP or domain.")
            return
        if not username or not password:
            QMessageBox.warning(self, "Missing Credentials", "Please enter NVR Username and Password.")
            return

        self.connect_btn.setEnabled(False)
        self.status_badge.setText("● Connecting...")
        self.status_badge.setStyleSheet(
            "background-color: #78350F; color: #F59E0B; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: bold; min-height: 24px; max-height: 28px;"
        )

        self._auth_worker = AuthWorker(
            host=host,
            port=port,
            username=username,
            password=password,
            auth_type=NVR_AUTH_TYPE,
            parent=self,
        )
        self._auth_worker.signal_log.connect(self.log_message)
        self._auth_worker.signal_finished.connect(self._on_auth_finished)
        self._auth_worker.start()

    def _on_auth_finished(self, success: bool, message: str, session: object) -> None:
        self.connect_btn.setEnabled(True)
        if success and isinstance(session, requests.Session):
            self._session = session
            self._save_credentials_if_checked()
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setProperty("connected", "true")
            self.connect_btn.style().unpolish(self.connect_btn)
            self.connect_btn.style().polish(self.connect_btn)
            self.status_badge.setText("● Connected")
            self.status_badge.setStyleSheet(
                "background-color: #064E3B; color: #10B981; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: bold; min-height: 24px; max-height: 28px;"
            )

            # Enable action search button
            self.search_btn.setEnabled(True)

            # Clear focus from input controls and focus search button
            self.host_input.clearFocus()
            self.user_input.clearFocus()
            self.password_input.clearFocus()
            self.search_btn.setFocus()

            self._trigger_discovery(force_refresh=False)
            self._trigger_dates_discovery()
        else:
            self._session = None
            self.connect_btn.setText("Connect")
            self.connect_btn.setProperty("connected", "false")
            self.connect_btn.style().unpolish(self.connect_btn)
            self.connect_btn.style().polish(self.connect_btn)
            self.status_badge.setText("● Auth Failed")
            self.status_badge.setStyleSheet(
                "background-color: #7F1D1D; color: #EF4444; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: bold; min-height: 24px; max-height: 28px;"
            )
            QMessageBox.critical(self, "Authentication Failed", f"Could not authenticate with NVR:\n{message}")

    @property
    def _camera_rows(self) -> list[CameraItem]:
        """Convenience property for accessing camera items in the table model."""
        return self._cameras_table_model.get_items()

    def _disconnect_session(self) -> None:
        """Disconnect active session, stop background workers, and perform full state purge."""
        if self._download_worker is not None and self._download_worker.isRunning():
            self._download_worker.cancel()
        if self._search_worker is not None and self._search_worker.isRunning():
            self._search_worker.cancel()
        if self._discovery_worker is not None and self._discovery_worker.isRunning():
            self._discovery_worker.quit()
            self._discovery_worker.wait(100)
        if self._dates_worker is not None and self._dates_worker.isRunning():
            self._dates_worker.quit()
            self._dates_worker.wait(100)

        # Clear session and discovered entities
        self._session = None
        self._discovered_cameras.clear()
        self._cameras_table_model.clear()
        self.cameras_stack.setCurrentIndex(0)
        self._discovered_dates.clear()
        self._device_info.clear()

        # Clear recordings table and reset stream options
        self.stream_combo.clear()
        self.stream_combo.setEnabled(False)
        self._table_model.clear()

        # Reset metric badges, progress, worker rows, and buttons
        self.discovered_badge.setText("0 Segments Discovered · 0 B")
        self.selected_badge.setText("0 Selected · 0 B")
        self.selected_badge.setStyleSheet(
            "background-color: #1E293B; color: #64748B; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; border: 1px solid #334155;"
        )
        self._reset_worker_rows()
        self.overall_progress_bar.setValue(0)
        self.progress_readout.setText("[  0% ]  Idle  |  0.0 Mbps  |  Elapsed: 00:00  |  ETA: --:--")
        self.start_download_btn.setEnabled(False)
        self.abort_btn.setEnabled(False)
        self.search_btn.setEnabled(False)

        # Reset connection button and status badge
        self.connect_btn.setText("Connect")
        self.connect_btn.setProperty("connected", "false")
        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)
        self.status_badge.setText("● Disconnected")
        self.status_badge.setStyleSheet(
            "background-color: #334155; color: #94A3B8; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: bold; min-height: 24px; max-height: 28px;"
        )
        self.footer_device_label.setText("Disconnected · Ready")

        # Clear connection inputs
        self.host_input.blockSignals(True)
        self.host_input.clear()
        self.host_input.setEditText("")
        self.host_input.blockSignals(False)

        self.port_input.setValue(80)

        self.user_input.blockSignals(True)
        self.user_input.clear()
        self.user_input.setEditText("")
        self.user_input.blockSignals(False)

        self.password_input.clear()
        self.password_input.setToolTip("")
        self.remember_cb.setChecked(True)

        # Reset recording time window
        self.date_picker.setDate(QDate.currentDate())
        cal = self.date_picker.calendarWidget()
        if cal is not None:
            cal.setDateTextFormat(QDate(), QTextCharFormat())

        self.start_hh_combo.setCurrentText("00")
        self.start_mm_combo.setCurrentText("00")
        self.end_hh_combo.setCurrentText("23")
        self.end_mm_combo.setCurrentText("59")

        # Clear console log completely
        self.console_log.clear()

    def _on_refresh_cameras_clicked(self) -> None:
        if self._session is None:
            self._on_connect_clicked()
        else:
            self._trigger_discovery(force_refresh=True)
            self._trigger_dates_discovery()

    def _trigger_discovery(self, force_refresh: bool) -> None:
        if self._session is None:
            return

        host = self.host_input.text()
        port = self.port_input.value()

        self._discovery_worker = DiscoveryWorker(
            session=self._session,
            host=host,
            port=port,
            force_refresh=force_refresh,
            parent=self,
        )
        self._discovery_worker.signal_log.connect(self.log_message)
        self._discovery_worker.signal_cameras.connect(self._on_discovery_cameras)
        self._discovery_worker.signal_device_info.connect(self._on_device_info_discovered)
        self._discovery_worker.signal_error.connect(lambda err: QMessageBox.warning(self, "Discovery Warning", err))
        self._discovery_worker.start()

    def _trigger_dates_discovery(self) -> None:
        if self._session is None:
            return

        host = self.host_input.text()

        self._dates_worker = DatesWorker(
            session=self._session,
            host=host,
            discovery_track_id=TrackId(101),
            parent=self,
        )
        self._dates_worker.signal_log.connect(self.log_message)
        self._dates_worker.signal_dates.connect(self._on_dates_discovered)
        self._dates_worker.start()

    def _on_device_info_discovered(self, info: object) -> None:
        if isinstance(info, dict):
            self._device_info = {str(k): str(v) for k, v in info.items()}
            model = self._device_info.get("model") or self._device_info.get("modelName") or "Hikvision NVR"
            fw = self._device_info.get("firmwareVersion") or "Unknown"
            count = len(self._discovered_cameras)
            self.footer_device_label.setText(f"Model: {model}  |  Firmware: {fw}  |  Active Cameras: {count}")

    def _on_dates_discovered(self, dates_by_month: object) -> None:
        if not isinstance(dates_by_month, dict):
            return

        self._discovered_dates = {k: v for k, v in dates_by_month.items() if isinstance(v, list)}
        cal = self.date_picker.calendarWidget()
        if cal is None:
            return

        char_format = QTextCharFormat()
        char_format.setBackground(QColor("#F37021"))
        char_format.setForeground(QColor("#FFFFFF"))
        char_format.setFontWeight(QFont.Weight.Bold)
        char_format.setToolTip("Footage Available")

        for rec_dates in self._discovered_dates.values():
            for rec_date in rec_dates:
                qdate = QDate(rec_date.year, rec_date.month, rec_date.day)
                cal.setDateTextFormat(qdate, char_format)

    def _on_discovery_cameras(self, cameras: dict[CameraNumber, Camera]) -> None:
        self._discovered_cameras = cameras
        self._cameras_table_model.set_cameras(cameras)
        if len(cameras) > 0:
            self.cameras_stack.setCurrentIndex(1)
        else:
            self.cameras_stack.setCurrentIndex(0)
        self._update_stream_options()

        if self._device_info:
            model = self._device_info.get("model") or self._device_info.get("modelName") or "Hikvision NVR"
            fw = self._device_info.get("firmwareVersion") or "Unknown"
            self.footer_device_label.setText(f"Model: {model}  |  Firmware: {fw}  |  Active Cameras: {len(cameras)}")
        elif self.footer_device_label.text() in ("Disconnected · Ready", "") or "Connected:" in self.footer_device_label.text():
            host = self.host_input.text()
            self.footer_device_label.setText(f"Connected: {host} ({len(cameras)} Cameras)")

    def _update_stream_options(self) -> None:
        """Update stream quality dropdown based on discovered camera tracks."""
        has_sub = any(int(cam.sub_track) > 0 or (cam.tracks and "sub" in cam.tracks) for cam in self._discovered_cameras.values())
        curr = str(self.stream_combo.currentData() or "HD")
        self.stream_combo.clear()
        self.stream_combo.addItem("HD (Main Stream)", "HD")
        if has_sub:
            self.stream_combo.addItem("SD (Sub Stream)", "SD")
            if curr == "SD":
                self.stream_combo.setCurrentIndex(1)
        self.stream_combo.setEnabled(len(self._discovered_cameras) > 0)

    def _rebuild_camera_checklist(self) -> None:
        """Refresh camera table model contents."""
        self._cameras_table_model.set_cameras(self._discovered_cameras)
        if len(self._discovered_cameras) > 0:
            self.cameras_stack.setCurrentIndex(1)
        else:
            self.cameras_stack.setCurrentIndex(0)

    def _set_all_cameras_checked(self, checked: bool) -> None:
        self._cameras_table_model.select_all(checked)

    def _apply_time_preset(self, start_hh: str, start_mm: str, end_hh: str, end_mm: str) -> None:
        self.start_hh_combo.setCurrentText(start_hh)
        self.start_mm_combo.setCurrentText(start_mm)
        self.end_hh_combo.setCurrentText(end_hh)
        self.end_mm_combo.setCurrentText(end_mm)

    def _on_output_dir_changed(self, text: str) -> None:
        self.output_dir_input.setToolTip(text)
        self._update_space_validation()

    def _on_browse_output_dir(self) -> None:
        curr = self.output_dir_input.text()
        chosen = QFileDialog.getExistingDirectory(self, "Select Output Directory", curr)
        if chosen:
            self.output_dir_input.setText(chosen)

    # =========================================================================
    # Event Handlers: Search CMSearch
    # =========================================================================

    def _on_search_clicked(self) -> None:
        if self._session is None:
            QMessageBox.warning(self, "Not Connected", "Please connect and authenticate with NVR first.")
            return

        selected_stream = str(self.stream_combo.currentData() or "HD")

        selected_cameras: list[tuple[Camera, str, TrackId]] = []
        for cam in self._cameras_table_model.get_selected_cameras():
            if selected_stream.upper() == "SD":
                track_id = cam.sub_track if int(cam.sub_track) > 0 else cam.main_track
            else:
                track_id = cam.main_track
            selected_cameras.append((cam, selected_stream, track_id))

        if not selected_cameras:
            QMessageBox.warning(self, "No Cameras Selected", "Please select at least one camera to search.")
            return

        qdate = self.date_picker.date()
        target_date = date(qdate.year(), qdate.month(), qdate.day())

        s_hh = int(self.start_hh_combo.currentText() or "0")
        s_mm = int(self.start_mm_combo.currentText() or "0")
        e_hh = int(self.end_hh_combo.currentText() or "23")
        e_mm = int(self.end_mm_combo.currentText() or "59")
        start_iso = f"{target_date.isoformat()}T{s_hh:02d}:{s_mm:02d}:00Z"
        end_iso = f"{target_date.isoformat()}T{e_hh:02d}:{e_mm:02d}:59Z"

        self._table_model.clear()
        self.search_btn.setEnabled(False)
        self.start_download_btn.setEnabled(False)

        host = self.host_input.text()
        port = self.port_input.value()

        self._search_worker = SearchWorker(
            session=self._session,
            host=host,
            port=port,
            camera_queries=selected_cameras,
            target_date=target_date,
            start_time_str=start_iso,
            end_time_str=end_iso,
            parent=self,
        )
        self._search_worker.signal_log.connect(self.log_message)
        self._search_worker.signal_camera_recordings.connect(self._on_camera_recordings_found)
        self._search_worker.signal_finished.connect(self._on_search_finished)
        self._search_worker.signal_error.connect(lambda err: QMessageBox.warning(self, "Search Warning", err))
        self._search_worker.start()

    def _on_camera_recordings_found(
        self,
        camera: object,
        stream_name: str,
        track_id: object,
        recordings: list[object],
    ) -> None:
        if not isinstance(camera, Camera) or not isinstance(track_id, int):
            return

        new_items: list[RecordingItem] = []
        for rec in recordings:
            if hasattr(rec, "name") and hasattr(rec, "size_bytes"):
                new_items.append(
                    RecordingItem(
                        recording=rec,  # type: ignore[arg-type]
                        camera=camera,
                        stream=stream_name,
                        track_id=TrackId(track_id),
                        checked=True,
                    )
                )

        current_items = list(self._table_model._items)
        current_items.extend(new_items)
        self._table_model.set_recordings(current_items)

    def _on_search_finished(self, total_count: int) -> None:
        self.search_btn.setEnabled(True)
        self._on_table_data_changed()
        if total_count == 0:
            self.log_message("INFO", "Search finished: No recordings found matching the specified time window.")

    # =========================================================================
    # Table & Pre-flight Space Validation
    # =========================================================================

    def _on_table_data_changed(self) -> None:
        total_count = self._table_model.get_total_count()
        selected_count = self._table_model.get_selected_count()
        total_bytes = sum(item.size_bytes for item in self._table_model._items)
        selected_bytes = self._table_model.get_total_selected_size()

        self.discovered_badge.setText(
            f"{total_count} Segments Discovered · {format_size_human(total_bytes)}"
        )
        if selected_count > 0:
            self.selected_badge.setText(
                f"✓ {selected_count} Selected · {format_size_human(selected_bytes)}"
            )
            self.selected_badge.setStyleSheet(
                "background-color: #0F2D37; color: #38BDF8; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; border: 1px solid #1E6B7B;"
            )
        else:
            self.selected_badge.setText("0 Selected · 0 B")
            self.selected_badge.setStyleSheet(
                "background-color: #1E293B; color: #64748B; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; border: 1px solid #334155;"
            )

        self.start_download_btn.setEnabled(
            selected_count > 0 and self._session is not None and (self._download_worker is None or not self._download_worker.isRunning())
        )
        self._update_space_validation()

    def _update_space_validation(self) -> None:
        out_text = self.output_dir_input.text().strip()
        if not out_text:
            self.space_label.setText("Disk: Invalid path")
            self.space_label.setStyleSheet(
                "background-color: #7F1D1D; color: #EF4444; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
            )
            return

        out_path = Path(out_text)
        selected_bytes = self._table_model.get_total_selected_size()
        has_space, req_b, free_b = check_disk_space(out_path, selected_bytes)

        if has_space:
            self.space_label.setText(f"Disk: {format_size_human(free_b)} Free ✓")
            self.space_label.setStyleSheet(
                "background-color: #064E3B; color: #10B981; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
            )
        else:
            self.space_label.setText(f"Disk: Insufficient! ({format_size_human(free_b)} Free vs {format_size_human(req_b)} Req) ⚠")
            self.space_label.setStyleSheet(
                "background-color: #7F1D1D; color: #EF4444; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
            )

    # =========================================================================
    # Event Handlers: Downloads & Cancellation
    # =========================================================================

    def _reset_worker_rows(self) -> None:
        """Reset and hide all visual worker progress slot rows."""
        self.worker_rows_container.setVisible(False)
        for w in self._worker_widgets.values():
            w.progress_bar.setValue(0)
            w.detail_label.setText("Idle")
            w.container.setVisible(False)
        for act in self._worker_activities.values():
            act.active = False
            act.filename = ""
            act.percent = 0
            act.speed_mb_s = 0.0

    def _on_start_download_clicked(self) -> None:
        if self._session is None:
            QMessageBox.warning(self, "Not Connected", "Please connect to NVR first.")
            return

        selected_items = self._table_model.get_selected_items()
        if not selected_items:
            QMessageBox.warning(self, "No Recordings Selected", "Please select at least one recording to download.")
            return

        out_path = Path(self.output_dir_input.text().strip())
        req_bytes = sum(item.size_bytes for item in selected_items)
        has_space, _, free_bytes = check_disk_space(out_path, req_bytes)

        if not has_space:
            resp = QMessageBox.question(
                self,
                "Disk Space Warning",
                f"The target volume has only {format_size_human(free_bytes)} free space, but the selected files require {format_size_human(req_bytes)}.\n\nDo you wish to proceed anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resp != QMessageBox.StandardButton.Yes:
                return

        self.start_download_btn.setEnabled(False)
        self.abort_btn.setEnabled(True)
        self.search_btn.setEnabled(False)
        self._batch_start_time = time.monotonic()
        self._total_batch_files = len(selected_items)
        self._total_batch_bytes = req_bytes
        self.overall_progress_bar.setValue(0)
        self.progress_readout.setText(
            f"[  0% ] 0/{self._total_batch_files} Files · 0 B / {format_size_human(self._total_batch_bytes)} · Elapsed: 00:00 · ETA: --:--"
        )

        host = self.host_input.text()
        port = self.port_input.value()
        username = self.user_input.text()
        password = self.password_input.text()
        workers = self.worker_slider.value()
        save_csv = self.csv_manifest_cb.isChecked()

        self._worker_activities.clear()
        self._file_to_worker.clear()
        self.worker_rows_container.setVisible(True)
        for wid in range(1, 5):
            w = self._worker_widgets[wid]
            if wid <= workers:
                w.container.setVisible(True)
                w.progress_bar.setValue(0)
                w.detail_label.setText("Idle")
                self._worker_activities[wid] = WorkerActivity(worker_id=wid)
            else:
                w.container.setVisible(False)

        self._download_worker = DownloadWorker(
            host=host,
            port=port,
            username=username,
            password=password,
            auth_type=NVR_AUTH_TYPE,
            selected_items=selected_items,
            output_root=out_path,
            max_workers=workers,
            save_csv=save_csv,
            parent=self,
        )
        self._download_worker.signal_log.connect(self.log_message)
        self._download_worker.signal_file_started.connect(self._on_file_started)
        self._download_worker.signal_progress.connect(self._on_download_progress)
        self._download_worker.signal_file_completed.connect(self._on_file_completed)
        self._download_worker.signal_finished.connect(self._on_download_finished)
        self._download_worker.signal_error.connect(lambda err: QMessageBox.critical(self, "Download Error", err))
        self._download_worker.start()

    def _on_file_started(self, filename: str, worker_id: int) -> None:
        """Handle worker starting download for a specific recording file."""
        self._file_to_worker[filename] = worker_id
        activity = self._worker_activities.get(worker_id)
        if activity is not None:
            activity.filename = filename
            activity.percent = 0
            activity.speed_mb_s = 0.0
            activity.active = True

        worker_widget = self._worker_widgets.get(worker_id)
        if worker_widget is not None:
            worker_widget.container.setVisible(True)
            self.worker_rows_container.setVisible(True)
            worker_widget.progress_bar.setValue(0)
            worker_widget.detail_label.setText(f"[{filename}] · 0% (0.0 MB/s)")

        self._table_model.update_item_status(filename=filename, status="Downloading")
        self._update_multi_worker_progress()

    def _on_download_progress(self, worker_id: int, prog: DownloadProgress) -> None:
        """Update live percentage in row status, per-worker visual progress bar, and overall batch summary."""
        if self._total_batch_files == 0 and prog.total_files > 0:
            self._total_batch_files = prog.total_files

        file_percent = int((prog.bytes_downloaded / max(prog.file_size_bytes, 1)) * 100)
        file_percent = max(0, min(file_percent, 100))
        speed_mb_s = float(prog.speed_mbps) / 8.0

        status_str = "Skipped" if prog.is_skipped else ("Completed" if prog.is_completed else f"Downloading ({file_percent}%)")
        self._table_model.update_item_status(
            filename=prog.filename,
            status=status_str,
            bytes_downloaded=int(prog.bytes_downloaded),
        )

        if worker_id not in self._worker_activities:
            self._worker_activities[worker_id] = WorkerActivity(worker_id=worker_id)
        act = self._worker_activities[worker_id]
        act.filename = prog.filename
        act.percent = file_percent
        act.speed_mb_s = speed_mb_s
        act.active = not (prog.is_completed or prog.is_skipped)

        worker_widget = self._worker_widgets.get(worker_id)
        if worker_widget is not None:
            worker_widget.container.setVisible(True)
            self.worker_rows_container.setVisible(True)
            worker_widget.progress_bar.setValue(file_percent)
            if prog.is_completed:
                worker_widget.detail_label.setText(f"[{prog.filename}] · Completed")
            elif prog.is_skipped:
                worker_widget.detail_label.setText(f"[{prog.filename}] · Skipped")
            else:
                worker_widget.detail_label.setText(f"[{prog.filename}] · {file_percent}% ({speed_mb_s:.1f} MB/s)")

        self._update_multi_worker_progress()

    def _update_multi_worker_progress(self) -> None:
        """Update overall batch progress bar and summary readout text."""
        total_files = max(self._total_batch_files, 1)
        total_bytes = getattr(self, "_total_batch_bytes", 0)

        selected_items = self._table_model.get_selected_items()
        completed_count = 0
        in_progress_fractions = 0.0
        downloaded_bytes = 0

        if selected_items:
            for item in selected_items:
                if item.status in ("Completed", "Skipped"):
                    completed_count += 1
                    downloaded_bytes += item.size_bytes
                elif item.status.startswith("Downloading"):
                    downloaded_bytes += item.actual_bytes
                    if item.size_bytes > 0:
                        in_progress_fractions += min(1.0, item.actual_bytes / item.size_bytes)
            overall_percent = int(((completed_count + in_progress_fractions) / total_files) * 100)
        else:
            active_pct_sum = sum(act.percent for act in self._worker_activities.values() if act.active)
            overall_percent = int((active_pct_sum / 100.0 / total_files) * 100)

        overall_percent = max(0, min(overall_percent, 100))
        self.overall_progress_bar.setValue(overall_percent)

        now = time.monotonic()
        batch_start = getattr(self, "_batch_start_time", now)
        elapsed = max(0.0, now - batch_start)
        elapsed_str = time.strftime("%M:%S", time.gmtime(int(elapsed)))

        if downloaded_bytes > 0 and elapsed > 0.5 and total_bytes > downloaded_bytes:
            bytes_per_sec = downloaded_bytes / elapsed
            remaining_bytes = total_bytes - downloaded_bytes
            eta_secs = remaining_bytes / bytes_per_sec if bytes_per_sec > 0 else 0
            eta_str = time.strftime("%M:%S", time.gmtime(int(eta_secs)))
        elif overall_percent >= 100 or (selected_items and completed_count == total_files):
            eta_str = "00:00"
        else:
            eta_str = "--:--"

        self.progress_readout.setText(
            f"[ {overall_percent:2d}% ] {completed_count}/{total_files} Files · {format_size_human(downloaded_bytes)} / {format_size_human(total_bytes)} · Elapsed: {elapsed_str} · ETA: {eta_str}"
        )

    def _on_file_completed(self, filename: str, status: str, is_skipped: bool) -> None:
        """Update status on file completion and mark worker slot inactive."""
        self._table_model.update_item_status(filename=filename, status=status)
        worker_id = self._file_to_worker.get(filename)
        if worker_id is not None and worker_id in self._worker_activities:
            self._worker_activities[worker_id].active = False

        if worker_id is not None and worker_id in self._worker_widgets:
            w = self._worker_widgets[worker_id]
            if status in ("Completed", "Skipped"):
                w.progress_bar.setValue(100)
                w.detail_label.setText(f"[{filename}] · {status}")
            elif status == "Aborted":
                w.detail_label.setText(f"[{filename}] · Aborted")
            elif status == "Failed":
                w.detail_label.setText(f"[{filename}] · Failed")

        self._update_multi_worker_progress()

    def _on_download_finished(self, result: DownloadResult) -> None:
        self.start_download_btn.setEnabled(True)
        self.abort_btn.setEnabled(False)
        self.search_btn.setEnabled(True)
        self.overall_progress_bar.setValue(100 if result.success else self.overall_progress_bar.value())

        status_text = (
            "Complete"
            if result.success
            else ("Aborted" if "abort" in str(result.error_message).lower() or "cancel" in str(result.error_message).lower() else "Failed")
        )
        elapsed_str = time.strftime("%M:%S", time.gmtime(int(result.total_duration_seconds)))
        percent = 100 if result.success else self.overall_progress_bar.value()
        self.progress_readout.setText(
            f"[ {percent:2d}% ] {status_text} ({result.downloaded_files} downloaded, {result.skipped_files} skipped) · Elapsed: {elapsed_str} · ETA: 00:00"
        )

        # Reset and hide worker rows
        self._reset_worker_rows()

        if result.success:
            QMessageBox.information(
                self,
                "Batch Download Complete",
                f"Successfully completed batch download!\n\n"
                f"• Downloaded: {result.downloaded_files} files ({format_size_human(int(result.downloaded_bytes))})\n"
                f"• Skipped: {result.skipped_files} files\n"
                f"• Duration: {result.total_duration_seconds:.1f}s",
            )
        elif result.error_message and "cancel" not in result.error_message.lower() and "abort" not in result.error_message.lower():
            QMessageBox.critical(self, "Download Incomplete", f"Batch download stopped with error:\n{result.error_message}")

    def _on_abort_clicked(self) -> None:
        if self._download_worker is not None and self._download_worker.isRunning():
            self.abort_btn.setEnabled(False)
            self.log_message("WARN", "Cancelling batch download. Waiting for active streams to terminate...")
            self._download_worker.cancel()
        if self._search_worker is not None and self._search_worker.isRunning():
            self._search_worker.cancel()

    def showEvent(self, event: QShowEvent) -> None:
        """Ensure splitter sizes and non-collapsible left panel upon first display."""
        super().showEvent(event)
        if hasattr(self, "main_splitter"):
            self.main_splitter.setSizes([420, max(self.width() - 420, 750)])
            self.main_splitter.setCollapsible(0, False)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure window geometry is persisted and background threads are terminated safely on window close."""
        save_window_geometry(self)
        if self._download_worker is not None and self._download_worker.isRunning():
            self._download_worker.cancel()
            self._download_worker.wait(2000)
        if self._search_worker is not None and self._search_worker.isRunning():
            self._search_worker.cancel()
            self._search_worker.wait(1000)
        if self._dates_worker is not None and self._dates_worker.isRunning():
            self._dates_worker.wait(1000)
        event.accept()


def main() -> None:
    """Entry point for the PySide6 Desktop GUI."""
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication(sys.argv)
    app.setApplicationName("HikVision Downloader")
    app.setOrganizationName("Arivedha")

    general_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    app.setFont(general_font)
    app.setStyleSheet(DARK_THEME_QSS)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
