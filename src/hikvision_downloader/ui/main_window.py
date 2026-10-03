"""Master Desktop GUI Application for Hikvision Downloader adhering to Arivedha design tokens."""

import os
import sys
import time
from datetime import date
from pathlib import Path

import requests
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
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
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
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
from .keychain import delete_nvr_password, get_nvr_password, save_nvr_password
from .models import (
    RecordingItem,
    RecordingsTableModel,
    check_disk_space,
    format_size_human,
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


class CameraRowWidget(QWidget):
    """Widget row for a camera inside the control panel list."""

    def __init__(self, camera: Camera, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.camera = camera
        self.setObjectName("cameraRow")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._layout.setSpacing(8)

        self.checkbox = QCheckBox(camera.display_name, self)
        self.checkbox.setChecked(True)
        self._layout.addWidget(self.checkbox, stretch=1)

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
            width = max(1240, min(1440, int(screen.width() * 0.85)))
            height = max(820, min(940, int(screen.height() * 0.85)))
            self.resize(width, height)
            self.move(screen.center() - self.rect().center())
        else:
            self.resize(1320, 880)
        self.setMinimumSize(1180, 760)

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
        self._camera_rows: list[CameraRowWidget] = []
        self._discovered_dates: dict[tuple[int, int], list[RecordingDate]] = {}

        # Active Workers
        self._auth_worker: AuthWorker | None = None
        self._discovery_worker: DiscoveryWorker | None = None
        self._dates_worker: DatesWorker | None = None
        self._search_worker: SearchWorker | None = None
        self._download_worker: DownloadWorker | None = None

        # Table Model
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

        # Load saved credentials and initial space check
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

        # Host
        form_layout.addWidget(QLabel("Host:", self))
        self.host_input = QLineEdit(self)
        self.host_input.setPlaceholderText("192.168.1.100")
        self.host_input.setMaximumWidth(120)
        self.host_input.setText(NVR_HOST or "")
        form_layout.addWidget(self.host_input)

        # Port
        form_layout.addWidget(QLabel("Port:", self))
        self.port_input = QSpinBox(self)
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(NVR_PORT or 80)
        self.port_input.setFixedWidth(50)
        self.port_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.port_input.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        form_layout.addWidget(self.port_input)

        # Username
        form_layout.addWidget(QLabel("User:", self))
        self.user_input = QLineEdit(self)
        self.user_input.setPlaceholderText("admin")
        self.user_input.setMaximumWidth(90)
        self.user_input.setText(NVR_USERNAME or "admin")
        form_layout.addWidget(self.user_input)

        # Password
        form_layout.addWidget(QLabel("Password:", self))
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setMaximumWidth(90)
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
        self.status_badge.setStyleSheet(
            "background-color: #334155; color: #94A3B8; border-radius: 8px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
        )
        h_layout.addWidget(self.status_badge)

        # Theme Switcher Button
        self.theme_btn = QPushButton("☀️", self)
        self.theme_btn.setObjectName("secondaryBtn")
        self.theme_btn.setFixedSize(32, 26)
        self.theme_btn.setToolTip("Toggle Light/Dark Theme")
        self.theme_btn.clicked.connect(self._toggle_theme)
        h_layout.addWidget(self.theme_btn)

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

        footer_brand = QLabel("Arivedha Surveillance Management Suite", self)
        footer_brand.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8; border: none; background: transparent;")
        brand_layout.addWidget(footer_brand)
        f_layout.addLayout(brand_layout)

        f_layout.addStretch(1)

        version_label = QLabel("v0.1.0-alpha • Automated ISAPI Engine", self)
        version_label.setStyleSheet("font-size: 11px; color: #64748B; border: none; background: transparent;")
        f_layout.addWidget(version_label)

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

        # 1. Camera Channels & Stream Quality Group
        left_layout.addWidget(self._build_camera_group())

        # 2. Investigation Time Window Group
        left_layout.addWidget(self._build_time_group())

        left_layout.addStretch(1)

        # 3. Pinned Search Button at bottom
        self.search_btn = QPushButton("🔍  SEARCH RECORDINGS", self)
        self.search_btn.setObjectName("searchBtn")
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

    def _build_camera_group(self) -> QGroupBox:
        group = QGroupBox("Camera Channels & Stream", self)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Quick Actions Bar
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        btn_select_all = QPushButton("Select All", self)
        btn_select_all.setObjectName("secondaryBtn")
        btn_select_all.clicked.connect(lambda: self._set_all_cameras_checked(True))
        actions_layout.addWidget(btn_select_all)

        btn_deselect_all = QPushButton("Deselect", self)
        btn_deselect_all.setObjectName("secondaryBtn")
        btn_deselect_all.clicked.connect(lambda: self._set_all_cameras_checked(False))
        actions_layout.addWidget(btn_deselect_all)

        btn_refresh = QPushButton("Refresh Channels", self)
        btn_refresh.setObjectName("secondaryBtn")
        btn_refresh.setMinimumWidth(110)
        btn_refresh.clicked.connect(self._on_refresh_cameras_clicked)
        actions_layout.addWidget(btn_refresh)

        layout.addLayout(actions_layout)

        # Camera Checklist Container (Scrollable)
        self.camera_list_container = QWidget(self)
        self.camera_list_layout = QVBoxLayout(self.camera_list_container)
        self.camera_list_layout.setContentsMargins(0, 4, 0, 4)
        self.camera_list_layout.setSpacing(4)

        self.empty_cam_label = QLabel("No cameras discovered. Click 'Connect' to discover channels.", self)
        self.empty_cam_label.setStyleSheet("color: #64748B; font-style: italic; padding: 12px;")
        self.empty_cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_list_layout.addWidget(self.empty_cam_label)

        self.camera_scroll = QScrollArea(self)
        self.camera_scroll.setWidgetResizable(True)
        self.camera_scroll.setWidget(self.camera_list_container)
        self.camera_scroll.setMaximumHeight(220)
        layout.addWidget(self.camera_scroll)

        # Stream Quality Dropdown
        stream_row = QHBoxLayout()
        stream_row.setSpacing(8)
        stream_label = QLabel("Stream Quality:", self)
        stream_row.addWidget(stream_label)

        self.stream_combo = QComboBox(self)
        self.stream_combo.addItem("HD (Main Stream)", "HD")
        stream_row.addWidget(self.stream_combo, stretch=1)
        layout.addLayout(stream_row)

        return group

    def _build_time_group(self) -> QGroupBox:
        group = QGroupBox("Investigation Time Window", self)
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

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

        return group

    def _build_download_settings_panel(self) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("downloadSettingsFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

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

        # Top Bar: Counters and Selection Actions
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.summary_label = QLabel("0 segments discovered (0 B) | 0 selected (0 B)", self)
        self.summary_label.setStyleSheet("font-weight: 600;")
        top_bar.addWidget(self.summary_label)

        top_bar.addStretch(1)

        btn_all = QPushButton("Select All", self)
        btn_all.setObjectName("secondaryBtn")
        btn_all.clicked.connect(lambda: self._table_model.select_all(True))
        top_bar.addWidget(btn_all)

        btn_none = QPushButton("Clear", self)
        btn_none.setObjectName("secondaryBtn")
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
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)

        # Set specific column widths
        self.table_view.setColumnWidth(RecordingsTableModel.COL_CHECK, 36)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_CAMERA, 140)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_STREAM, 65)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_FILENAME, 220)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_START, 150)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_END, 150)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_SIZE, 90)
        self.table_view.setColumnWidth(RecordingsTableModel.COL_STATUS, 100)

        layout.addWidget(self.table_view)
        return panel

    def _build_console_log_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("cardFrame")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Header bar with integrated telemetry progress
        header_bar = QHBoxLayout()
        header_bar.setSpacing(10)
        header_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        console_title = QLabel("Live Activity Console", self)
        console_title.setStyleSheet("font-weight: bold; color: #38BDF8; font-size: 12px;")
        header_bar.addWidget(console_title)

        # Integrated progress bar & telemetry indicators
        self.overall_progress_bar = QProgressBar(self)
        self.overall_progress_bar.setRange(0, 100)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setFixedHeight(14)
        self.overall_progress_bar.setMinimumWidth(100)
        header_bar.addWidget(self.overall_progress_bar, stretch=1)

        self.progress_status_label = QLabel("Idle", self)
        self.progress_status_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        header_bar.addWidget(self.progress_status_label)

        self.progress_speed_label = QLabel("0.0 Mbps", self)
        self.progress_speed_label.setStyleSheet("color: #F37021; font-size: 11px; font-weight: bold;")
        header_bar.addWidget(self.progress_speed_label)

        self.progress_eta_label = QLabel("Elapsed: 00:00", self)
        self.progress_eta_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        header_bar.addWidget(self.progress_eta_label)

        clear_btn = QPushButton("Clear", self)
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.setFixedHeight(22)
        clear_btn.clicked.connect(self._on_clear_console)
        header_bar.addWidget(clear_btn)

        layout.addLayout(header_bar)

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
    # Credential & Keychain Logic
    # =========================================================================

    def _load_initial_credentials(self) -> None:
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()
        port = self.port_input.value()

        if host and user:
            saved_pw = get_nvr_password(host, user, port)
            if saved_pw:
                self.password_input.setText(saved_pw)
                self.remember_cb.setChecked(True)
                self.log_message("INFO", f"Loaded stored credentials from OS Keychain for {host}:{port}.")
            elif NVR_PASSWORD:
                self.password_input.setText(NVR_PASSWORD)

    def _save_credentials_if_checked(self) -> None:
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()
        port = self.port_input.value()
        password = self.password_input.text()

        if self.remember_cb.isChecked() and host and user and password:
            if save_nvr_password(host, user, password, port):
                self.log_message("INFO", "NVR credentials saved securely to OS Keychain.")
            else:
                self.log_message("WARN", "Could not persist credentials to OS Keychain.")
        elif not self.remember_cb.isChecked() and host and user:
            delete_nvr_password(host, user, port)

    # =========================================================================
    # Logging & Console Output
    # =========================================================================

    def log_message(self, level: str, message: str) -> None:
        """Append a timestamped log line to the live activity console."""
        timestamp = time.strftime("%H:%M:%S")
        color_map = {
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

        host = self.host_input.text().strip()
        port = self.port_input.value()
        username = self.user_input.text().strip()
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
            "background-color: #78350F; color: #F59E0B; border-radius: 8px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
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
                "background-color: #064E3B; color: #10B981; border-radius: 8px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
            )
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
                "background-color: #7F1D1D; color: #EF4444; border-radius: 8px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
            )
            QMessageBox.critical(self, "Authentication Failed", f"Could not authenticate with NVR:\n{message}")

    def _disconnect_session(self) -> None:
        """Disconnect active session, stop background workers, and reset UI state."""
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
        self._session = None
        self._discovered_cameras.clear()
        self._camera_rows.clear()
        self._discovered_dates.clear()
        self._rebuild_camera_checklist()
        self._update_stream_options()
        self._table_model.clear()
        self.connect_btn.setText("Connect")
        self.connect_btn.setProperty("connected", "false")
        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)
        self.status_badge.setText("● Disconnected")
        self.status_badge.setStyleSheet(
            "background-color: #334155; color: #94A3B8; border-radius: 8px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
        )
        self.log_message("INFO", "Disconnected from NVR session.")

    def _on_refresh_cameras_clicked(self) -> None:
        if self._session is None:
            self._on_connect_clicked()
        else:
            self._trigger_discovery(force_refresh=True)
            self._trigger_dates_discovery()

    def _trigger_discovery(self, force_refresh: bool) -> None:
        if self._session is None:
            return

        host = self.host_input.text().strip()
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
        self._discovery_worker.signal_error.connect(lambda err: QMessageBox.warning(self, "Discovery Warning", err))
        self._discovery_worker.start()

    def _trigger_dates_discovery(self) -> None:
        if self._session is None:
            return

        host = self.host_input.text().strip()

        self._dates_worker = DatesWorker(
            session=self._session,
            host=host,
            discovery_track_id=TrackId(101),
            parent=self,
        )
        self._dates_worker.signal_log.connect(self.log_message)
        self._dates_worker.signal_dates.connect(self._on_dates_discovered)
        self._dates_worker.start()

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
        self._rebuild_camera_checklist()
        self._update_stream_options()

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

    def _rebuild_camera_checklist(self) -> None:
        for row_widget in self._camera_rows:
            self.camera_list_layout.removeWidget(row_widget)
            row_widget.deleteLater()
        self._camera_rows.clear()

        if not self._discovered_cameras:
            self.empty_cam_label.setVisible(True)
            return

        self.empty_cam_label.setVisible(False)

        for _, camera in sorted(self._discovered_cameras.items(), key=lambda x: int(x[0])):
            row = CameraRowWidget(camera, self.camera_list_container)
            self.camera_list_layout.addWidget(row)
            self._camera_rows.append(row)

    def _set_all_cameras_checked(self, checked: bool) -> None:
        for row in self._camera_rows:
            row.checkbox.setChecked(checked)

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
        for row in self._camera_rows:
            if row.is_selected:
                if selected_stream.upper() == "SD":
                    track_id = row.camera.sub_track if int(row.camera.sub_track) > 0 else row.camera.main_track
                else:
                    track_id = row.camera.main_track
                selected_cameras.append((row.camera, selected_stream, track_id))

        if not selected_cameras:
            QMessageBox.warning(self, "No Cameras Selected", "Please select at least one camera channel to search.")
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

        host = self.host_input.text().strip()
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

        self.summary_label.setText(
            f"{total_count} segments discovered ({format_size_human(total_bytes)}) | {selected_count} selected ({format_size_human(selected_bytes)})"
        )
        self.start_download_btn.setEnabled(selected_count > 0 and (self._download_worker is None or not self._download_worker.isRunning()))
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
        self.overall_progress_bar.setValue(0)
        self.progress_status_label.setText("Preparing batch download...")

        host = self.host_input.text().strip()
        port = self.port_input.value()
        workers = self.worker_slider.value()
        save_csv = self.csv_manifest_cb.isChecked()

        self._download_worker = DownloadWorker(
            session=self._session,
            host=host,
            port=port,
            selected_items=selected_items,
            output_root=out_path,
            max_workers=workers,
            save_csv=save_csv,
            parent=self,
        )
        self._download_worker.signal_log.connect(self.log_message)
        self._download_worker.signal_progress.connect(self._on_download_progress)
        self._download_worker.signal_file_completed.connect(self._on_file_completed)
        self._download_worker.signal_finished.connect(self._on_download_finished)
        self._download_worker.signal_error.connect(lambda err: QMessageBox.critical(self, "Download Error", err))
        self._download_worker.start()

    def _on_download_progress(self, prog: DownloadProgress) -> None:
        total_files = max(prog.total_files, 1)
        curr_idx = prog.current_index
        percent = int(((curr_idx - 1) + (prog.bytes_downloaded / max(prog.file_size_bytes, 1))) / total_files * 100)
        percent = max(0, min(percent, 100))

        self.overall_progress_bar.setValue(percent)
        self.progress_status_label.setText(f"[{curr_idx}/{total_files}] {prog.filename}")
        self.progress_speed_label.setText(f"{float(prog.speed_mbps):.1f} Mbps")

        elapsed_str = time.strftime("%M:%S", time.gmtime(prog.elapsed_seconds))
        self.progress_eta_label.setText(f"Elapsed: {elapsed_str}")

        self._table_model.update_item_status(
            filename=prog.filename,
            status="Skipped" if prog.is_skipped else ("Completed" if prog.is_completed else "Downloading"),
            bytes_downloaded=int(prog.bytes_downloaded),
        )

    def _on_file_completed(self, filename: str, status: str, is_skipped: bool) -> None:
        self._table_model.update_item_status(filename=filename, status=status)

    def _on_download_finished(self, result: DownloadResult) -> None:
        self.start_download_btn.setEnabled(True)
        self.abort_btn.setEnabled(False)
        self.search_btn.setEnabled(True)
        self.overall_progress_bar.setValue(100 if result.success else self.overall_progress_bar.value())

        status_text = "Complete" if result.success else ("Cancelled" if "cancelled" in str(result.error_message).lower() else "Failed")
        self.progress_status_label.setText(f"{status_text} ({result.downloaded_files} downloaded, {result.skipped_files} skipped)")
        self.progress_speed_label.setText("0.0 Mbps")

        if result.success:
            QMessageBox.information(
                self,
                "Batch Download Complete",
                f"Successfully completed batch download!\n\n"
                f"• Downloaded: {result.downloaded_files} files ({format_size_human(int(result.downloaded_bytes))})\n"
                f"• Skipped: {result.skipped_files} files\n"
                f"• Duration: {result.total_duration_seconds:.1f}s",
            )
        elif result.error_message and "cancelled" not in result.error_message.lower():
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
        """Ensure background threads are terminated safely on window close."""
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
