"""Master PySide6 desktop application window for HikVision Downloader by Arivedha."""

import sys
import time
from datetime import date
from pathlib import Path

import requests
from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtGui import QCloseEvent, QIcon, QPixmap
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
    QTimeEdit,
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
    OUTPUT_ROOT,
)
from ..core.models import Camera, CameraNumber, DownloadProgress, DownloadResult, TrackId
from .keychain import delete_nvr_password, get_nvr_password, save_nvr_password
from .models import RecordingItem, RecordingsTableModel, check_disk_space, format_size_human
from .style import DARK_THEME_QSS
from .workers import AuthWorker, DiscoveryWorker, DownloadWorker, SearchWorker

ASSETS_DIR: Path = Path(__file__).resolve().parent / "assets"
LOGO_SVG_PATH: Path = ASSETS_DIR / "logo.svg"
FAVICON_SVG_PATH: Path = ASSETS_DIR / "favicon.svg"


class CameraRowWidget(QWidget):
    """Widget row for a camera inside the control panel list."""

    def __init__(self, camera: Camera, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.camera = camera
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 2, 4, 2)
        self._layout.setSpacing(8)

        self.checkbox = QCheckBox(camera.display_name, self)
        self.checkbox.setChecked(True)
        self._layout.addWidget(self.checkbox, stretch=1)

        self.stream_combo = QComboBox(self)
        self.stream_combo.addItem("HD (Main)", "HD")
        if int(camera.sub_track) > 0 or (camera.tracks and "sub" in camera.tracks):
            self.stream_combo.addItem("SD (Sub)", "SD")
        self.stream_combo.setFixedWidth(100)
        self._layout.addWidget(self.stream_combo)

    @property
    def is_selected(self) -> bool:
        return self.checkbox.isChecked()

    @property
    def selected_stream(self) -> str:
        data = self.stream_combo.currentData()
        return str(data) if data is not None else "HD"

    def get_track_id(self) -> TrackId:
        stream = self.selected_stream.lower()
        if stream == "hd":
            return self.camera.main_track
        return self.camera.sub_track if int(self.camera.sub_track) > 0 else self.camera.main_track


class MainWindow(QMainWindow):
    """Master desktop application window orchestrating the operator console."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HikVision Downloader by Arivedha")
        self.resize(1280, 840)
        self.setMinimumSize(1024, 700)

        # Apply application icon
        if FAVICON_SVG_PATH.exists():
            self.setWindowIcon(QIcon(str(FAVICON_SVG_PATH)))
        elif LOGO_SVG_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_SVG_PATH)))

        # Session & State
        self._session: requests.Session | None = None
        self._discovered_cameras: dict[CameraNumber, Camera] = {}
        self._camera_rows: list[CameraRowWidget] = []

        # Active Workers
        self._auth_worker: AuthWorker | None = None
        self._discovery_worker: DiscoveryWorker | None = None
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
        self._load_initial_credentials()
        self._update_space_validation()

    # =========================================================================
    # UI Construction: Top Header Bar
    # =========================================================================

    def _build_top_header(self) -> None:
        header = QFrame(self)
        header.setObjectName("headerFrame")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 10, 16, 10)
        h_layout.setSpacing(16)

        # Brand / Logo
        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(10)

        logo_label = QLabel(self)
        if FAVICON_SVG_PATH.exists():
            pix = QPixmap(str(FAVICON_SVG_PATH)).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pix)
        logo_label.setFixedSize(36, 36)
        brand_layout.addWidget(logo_label)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)
        title_label = QLabel("HikVision Downloader", self)
        title_label.setStyleSheet("font-size: 16px; font-weight: 800; color: #F8FAFC;")
        sub_label = QLabel("by Arivedha", self)
        sub_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #F37021; text-transform: uppercase; letter-spacing: 1px;")
        title_layout.addWidget(title_label)
        title_layout.addWidget(sub_label)
        brand_layout.addLayout(title_layout)
        h_layout.addLayout(brand_layout)

        h_layout.addSpacing(12)

        # Connection Form Inputs
        form_layout = QHBoxLayout()
        form_layout.setSpacing(8)

        # Host
        form_layout.addWidget(QLabel("Host:", self))
        self.host_input = QLineEdit(self)
        self.host_input.setPlaceholderText("192.168.1.100")
        self.host_input.setFixedWidth(130)
        self.host_input.setText(NVR_HOST or "")
        form_layout.addWidget(self.host_input)

        # Port
        form_layout.addWidget(QLabel("Port:", self))
        self.port_input = QSpinBox(self)
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(NVR_PORT or 80)
        self.port_input.setFixedWidth(70)
        form_layout.addWidget(self.port_input)

        # Username
        form_layout.addWidget(QLabel("User:", self))
        self.user_input = QLineEdit(self)
        self.user_input.setPlaceholderText("admin")
        self.user_input.setFixedWidth(100)
        self.user_input.setText(NVR_USERNAME or "admin")
        form_layout.addWidget(self.user_input)

        # Password
        form_layout.addWidget(QLabel("Password:", self))
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setFixedWidth(120)
        form_layout.addWidget(self.password_input)

        # Remember in Keychain Checkbox
        self.remember_cb = QCheckBox("Save in Keychain", self)
        self.remember_cb.setChecked(True)
        form_layout.addWidget(self.remember_cb)

        # Connect / Authenticate Button
        self.connect_btn = QPushButton("Connect", self)
        self.connect_btn.setObjectName("secondaryBtn")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        form_layout.addWidget(self.connect_btn)

        h_layout.addLayout(form_layout)
        h_layout.addStretch(1)

        # Status Badge Pill
        self.status_badge = QLabel("● Disconnected", self)
        self.status_badge.setObjectName("statusBadge")
        self.status_badge.setStyleSheet("background-color: #334155; color: #94A3B8; border-radius: 12px; padding: 5px 12px; font-weight: 600;")
        h_layout.addWidget(self.status_badge)

        self._root_layout.addWidget(header)

    # =========================================================================
    # UI Construction: Body Splitter & Panels
    # =========================================================================

    def _build_body_panels(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(4)

        # Left Control Panel
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 6, 12)
        left_layout.setSpacing(12)

        left_scroll = QScrollArea(left_widget)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 4, 0)
        scroll_layout.setSpacing(12)

        # 1. Cameras Group
        scroll_layout.addWidget(self._build_camera_group())

        # 2. Investigation Window Group
        scroll_layout.addWidget(self._build_time_window_group())

        # 3. Download Options Group
        scroll_layout.addWidget(self._build_options_group())

        # Search Segments Button
        self.search_btn = QPushButton("🔍  SEARCH RECORDINGS", self)
        self.search_btn.setObjectName("primaryActionBtn")
        self.search_btn.setStyleSheet("background-color: #1E6B7B; font-size: 13px;")
        self.search_btn.clicked.connect(self._on_search_clicked)
        scroll_layout.addWidget(self.search_btn)

        scroll_layout.addStretch(1)
        left_scroll.setWidget(scroll_content)
        left_layout.addWidget(left_scroll)
        splitter.addWidget(left_widget)

        # Right Operational Panel
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 12, 12, 12)
        right_layout.setSpacing(10)

        # Discovered Segments Table & Action Bar
        right_layout.addWidget(self._build_recordings_view_panel(), stretch=6)

        # Progress Section
        right_layout.addWidget(self._build_progress_section(), stretch=0)

        # Activity Log Console
        right_layout.addWidget(self._build_console_log_panel(), stretch=4)

        splitter.addWidget(right_widget)
        splitter.setSizes([380, 900])
        self._root_layout.addWidget(splitter)

    def _build_camera_group(self) -> QGroupBox:
        group = QGroupBox("Camera Channels & Streams", self)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Quick Actions Bar
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        btn_select_all = QPushButton("Select All", self)
        btn_select_all.setObjectName("secondaryBtn")
        btn_select_all.clicked.connect(lambda: self._set_all_cameras_checked(True))
        actions_layout.addWidget(btn_select_all)

        btn_deselect_all = QPushButton("Deselect", self)
        btn_deselect_all.setObjectName("secondaryBtn")
        btn_deselect_all.clicked.connect(lambda: self._set_all_cameras_checked(False))
        actions_layout.addWidget(btn_deselect_all)

        btn_refresh = QPushButton("Refresh", self)
        btn_refresh.setObjectName("secondaryBtn")
        btn_refresh.clicked.connect(self._on_refresh_cameras_clicked)
        actions_layout.addWidget(btn_refresh)

        layout.addLayout(actions_layout)

        # Global Stream Selector
        stream_bar = QHBoxLayout()
        stream_bar.addWidget(QLabel("Global Stream:", self))
        self.global_stream_combo = QComboBox(self)
        self.global_stream_combo.addItems(["Custom Per-Camera", "All HD (Main Stream)", "All SD (Sub Stream)"])
        self.global_stream_combo.currentIndexChanged.connect(self._on_global_stream_changed)
        stream_bar.addWidget(self.global_stream_combo)
        layout.addLayout(stream_bar)

        # Camera Checklist Container (Scrollable)
        self.camera_list_container = QWidget(self)
        self.camera_list_layout = QVBoxLayout(self.camera_list_container)
        self.camera_list_layout.setContentsMargins(0, 4, 0, 4)
        self.camera_list_layout.setSpacing(4)

        self.empty_cam_label = QLabel("No cameras discovered. Click 'Connect' to discover channels.", self)
        self.empty_cam_label.setStyleSheet("color: #64748B; font-style: italic; padding: 12px;")
        self.empty_cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_list_layout.addWidget(self.empty_cam_label)

        layout.addWidget(self.camera_list_container)
        return group

    def _build_time_window_group(self) -> QGroupBox:
        group = QGroupBox("Investigation Time Window", self)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Date Picker (Defaults to Yesterday)
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date:", self))
        self.date_picker = QDateEdit(self)
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        yesterday = QDate.currentDate().addDays(-1)
        self.date_picker.setDate(yesterday)
        date_layout.addWidget(self.date_picker)
        layout.addLayout(date_layout)

        # Full Day Checkbox
        self.full_day_cb = QCheckBox("Full Day (00:00:00 - 23:59:59)", self)
        self.full_day_cb.setChecked(True)
        self.full_day_cb.toggled.connect(self._on_full_day_toggled)
        layout.addWidget(self.full_day_cb)

        # Custom Time Range (Hidden/Disabled by default)
        self.time_range_widget = QWidget(self)
        time_layout = QHBoxLayout(self.time_range_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(6)

        time_layout.addWidget(QLabel("From:", self))
        self.start_time_edit = QTimeEdit(self)
        self.start_time_edit.setDisplayFormat("HH:mm:ss")
        self.start_time_edit.setTime(QTime(0, 0, 0))
        time_layout.addWidget(self.start_time_edit)

        time_layout.addWidget(QLabel("To:", self))
        self.end_time_edit = QTimeEdit(self)
        self.end_time_edit.setDisplayFormat("HH:mm:ss")
        self.end_time_edit.setTime(QTime(23, 59, 59))
        time_layout.addWidget(self.end_time_edit)

        self.time_range_widget.setEnabled(False)
        layout.addWidget(self.time_range_widget)

        return group

    def _build_options_group(self) -> QGroupBox:
        group = QGroupBox("Download Settings", self)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Concurrency Slider (1-4)
        conc_layout = QHBoxLayout()
        conc_layout.addWidget(QLabel("Concurrent Workers:", self))
        self.worker_label = QLabel(f"{NVR_MAX_WORKERS}", self)
        self.worker_label.setStyleSheet("color: #38BDF8; font-weight: bold;")
        conc_layout.addWidget(self.worker_label)
        conc_layout.addStretch(1)
        layout.addLayout(conc_layout)

        self.worker_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.worker_slider.setRange(1, 4)
        self.worker_slider.setValue(NVR_MAX_WORKERS)
        self.worker_slider.setTickInterval(1)
        self.worker_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.worker_slider.valueChanged.connect(lambda v: self.worker_label.setText(str(v)))
        layout.addWidget(self.worker_slider)

        # Output Directory Selector
        dir_label_layout = QHBoxLayout()
        dir_label_layout.addWidget(QLabel("Output Directory:", self))
        layout.addLayout(dir_label_layout)

        dir_input_layout = QHBoxLayout()
        self.output_dir_input = QLineEdit(self)
        self.output_dir_input.setText(str(OUTPUT_ROOT.resolve()))
        self.output_dir_input.textChanged.connect(self._update_space_validation)
        dir_input_layout.addWidget(self.output_dir_input)

        browse_btn = QPushButton("Browse...", self)
        browse_btn.setObjectName("secondaryBtn")
        browse_btn.clicked.connect(self._on_browse_output_dir)
        dir_input_layout.addWidget(browse_btn)
        layout.addLayout(dir_input_layout)

        # Free Space Readout
        self.space_label = QLabel("Disk Space: Checking...", self)
        self.space_label.setStyleSheet("font-size: 11px; color: #94A3B8;")
        layout.addWidget(self.space_label)

        # CSV Manifest
        self.csv_manifest_cb = QCheckBox("Generate recording-list.csv manifest", self)
        self.csv_manifest_cb.setChecked(True)
        layout.addWidget(self.csv_manifest_cb)

        return group

    def _build_recordings_view_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("cardFrame")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Top Bar: Counters and Range Selector
        top_bar = QHBoxLayout()

        self.summary_label = QLabel("0 segments discovered (0.0 MB) | 0 selected (0.0 MB)", self)
        self.summary_label.setStyleSheet("font-weight: 600; color: #E2E8F0;")
        top_bar.addWidget(self.summary_label)

        top_bar.addStretch(1)

        # Range Selector Controls
        top_bar.addWidget(QLabel("Range:", self))
        self.range_start_spin = QSpinBox(self)
        self.range_start_spin.setRange(1, 9999)
        self.range_start_spin.setValue(1)
        self.range_start_spin.setFixedWidth(60)
        top_bar.addWidget(self.range_start_spin)

        top_bar.addWidget(QLabel("Count:", self))
        self.range_count_spin = QSpinBox(self)
        self.range_count_spin.setRange(1, 9999)
        self.range_count_spin.setValue(10)
        self.range_count_spin.setFixedWidth(60)
        top_bar.addWidget(self.range_count_spin)

        apply_range_btn = QPushButton("Select Range", self)
        apply_range_btn.setObjectName("secondaryBtn")
        apply_range_btn.clicked.connect(self._on_apply_range_clicked)
        top_bar.addWidget(apply_range_btn)

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

        # Primary Action Row: START BATCH DOWNLOAD and CANCEL
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self.start_download_btn = QPushButton("🚀  START BATCH DOWNLOAD", self)
        self.start_download_btn.setObjectName("primaryActionBtn")
        self.start_download_btn.setEnabled(False)
        self.start_download_btn.clicked.connect(self._on_start_download_clicked)
        action_row.addWidget(self.start_download_btn, stretch=3)

        self.abort_btn = QPushButton("✕  CANCEL / ABORT", self)
        self.abort_btn.setObjectName("abortBtn")
        self.abort_btn.setEnabled(False)
        self.abort_btn.clicked.connect(self._on_abort_clicked)
        action_row.addWidget(self.abort_btn, stretch=1)

        layout.addLayout(action_row)
        return panel

    def _build_progress_section(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("cardFrame")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Metrics Readout Bar
        metrics_layout = QHBoxLayout()
        self.prog_status_label = QLabel("Idle", self)
        self.prog_status_label.setStyleSheet("font-weight: 600; color: #38BDF8;")
        metrics_layout.addWidget(self.prog_status_label)

        metrics_layout.addStretch(1)

        self.speed_label = QLabel("0.0 Mbps", self)
        self.speed_label.setStyleSheet("font-weight: 600; color: #F37021;")
        metrics_layout.addWidget(self.speed_label)

        metrics_layout.addSpacing(12)
        self.time_label = QLabel("Elapsed: 00:00 | ETA: --:--", self)
        self.time_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        metrics_layout.addWidget(self.time_label)

        layout.addLayout(metrics_layout)

        # Overall Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        return panel

    def _build_console_log_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("cardFrame")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Live Activity Console", self))
        header_layout.addStretch(1)

        clear_btn = QPushButton("Clear Console", self)
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.clicked.connect(self._on_clear_console)
        header_layout.addWidget(clear_btn)

        layout.addLayout(header_layout)

        self.console_log = QPlainTextEdit(self)
        self.console_log.setObjectName("consoleLog")
        self.console_log.setReadOnly(True)
        self.console_log.setMaximumBlockCount(1000)
        layout.addWidget(self.console_log)

        return panel

    # =========================================================================
    # Credential & Keychain Logic
    # =========================================================================

    def _load_initial_credentials(self) -> None:
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()
        port = self.port_input.value()

        # Try retrieving password from OS keychain
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
            "SUCCESS": "#10B981",
            "WARN": "#F59E0B",
            "ERROR": "#EF4444",
            "SKIP": "#EAB308",
            "DOWNLOAD": "#F37021",
        }
        color = color_map.get(level.upper(), "#94A3B8")
        line = f"<span style='color: #64748B;'>[{timestamp}]</span> <span style='color: {color}; font-weight: bold;'>[{level.upper()}]</span> <span style='color: #F8FAFC;'>{message}</span>"
        self.console_log.appendHtml(line)
        self.console_log.verticalScrollBar().setValue(self.console_log.verticalScrollBar().maximum())

    def _on_clear_console(self) -> None:
        self.console_log.clear()

    # =========================================================================
    # Event Handlers: Connection & Discovery
    # =========================================================================

    def _on_connect_clicked(self) -> None:
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
        self.status_badge.setStyleSheet("background-color: #78350F; color: #F59E0B; border-radius: 12px; padding: 5px 12px; font-weight: 600;")

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
            self.status_badge.setText("● Connected")
            self.status_badge.setStyleSheet("background-color: #064E3B; color: #10B981; border-radius: 12px; padding: 5px 12px; font-weight: 600;")
            self._trigger_discovery(force_refresh=False)
        else:
            self._session = None
            self.status_badge.setText("● Auth Failed")
            self.status_badge.setStyleSheet("background-color: #7F1D1D; color: #EF4444; border-radius: 12px; padding: 5px 12px; font-weight: 600;")
            QMessageBox.critical(self, "Authentication Failed", f"Could not authenticate with NVR:\n{message}")

    def _on_refresh_cameras_clicked(self) -> None:
        if self._session is None:
            self._on_connect_clicked()
        else:
            self._trigger_discovery(force_refresh=True)

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

    def _on_discovery_cameras(self, cameras: dict[CameraNumber, Camera]) -> None:
        self._discovered_cameras = cameras
        self._rebuild_camera_checklist()

    def _rebuild_camera_checklist(self) -> None:
        # Clear existing rows
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

    def _on_global_stream_changed(self, index: int) -> None:
        if index == 1:  # All HD
            for row in self._camera_rows:
                idx = row.stream_combo.findData("HD")
                if idx >= 0:
                    row.stream_combo.setCurrentIndex(idx)
        elif index == 2:  # All SD
            for row in self._camera_rows:
                idx = row.stream_combo.findData("SD")
                if idx >= 0:
                    row.stream_combo.setCurrentIndex(idx)

    def _on_full_day_toggled(self, checked: bool) -> None:
        self.time_range_widget.setEnabled(not checked)

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

        selected_cameras: list[tuple[Camera, str, TrackId]] = []
        for row in self._camera_rows:
            if row.is_selected:
                stream = row.selected_stream
                track_id = row.get_track_id()
                selected_cameras.append((row.camera, stream, track_id))

        if not selected_cameras:
            QMessageBox.warning(self, "No Cameras Selected", "Please select at least one camera channel to search.")
            return

        qdate = self.date_picker.date()
        target_date = date(qdate.year(), qdate.month(), qdate.day())

        if self.full_day_cb.isChecked():
            start_iso = f"{target_date.isoformat()}T00:00:00Z"
            end_iso = f"{target_date.isoformat()}T23:59:59Z"
        else:
            q_start = self.start_time_edit.time()
            q_end = self.end_time_edit.time()
            start_iso = f"{target_date.isoformat()}T{q_start.hour():02d}:{q_start.minute():02d}:{q_start.second():02d}Z"
            end_iso = f"{target_date.isoformat()}T{q_end.hour():02d}:{q_end.minute():02d}:{q_end.second():02d}Z"

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
            if hasattr(rec, "name"):
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
        self._update_space_validation()

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
        out_dir = self.output_dir_input.text().strip()
        selected_bytes = self._table_model.get_total_selected_size()
        has_space, req_b, free_b = check_disk_space(out_dir or ".", selected_bytes)

        if free_b == 0:
            self.space_label.setText("Disk Space: Unable to query volume")
            self.space_label.setStyleSheet("font-size: 11px; color: #94A3B8;")
        elif has_space:
            self.space_label.setText(f"Disk Space: {format_size_human(free_b)} Free | Required: {format_size_human(req_b)} (OK ✓)")
            self.space_label.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 600;")
        else:
            self.space_label.setText(f"Disk Space: Insufficient! {format_size_human(free_b)} Free vs {format_size_human(req_b)} Required ⚠")
            self.space_label.setStyleSheet("font-size: 11px; color: #EF4444; font-weight: bold;")

    def _on_apply_range_clicked(self) -> None:
        start_idx = self.range_start_spin.value()
        count = self.range_count_spin.value()
        self._table_model.select_range(start_idx, count)

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
        self.progress_bar.setValue(0)
        self.prog_status_label.setText("Preparing batch download...")

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

        self.progress_bar.setValue(percent)
        self.prog_status_label.setText(f"Downloading [{curr_idx}/{total_files}]: {prog.filename}")
        self.speed_label.setText(f"{float(prog.speed_mbps):.1f} Mbps")

        elapsed_str = time.strftime("%M:%S", time.gmtime(prog.elapsed_seconds))
        self.time_label.setText(f"File Elapsed: {elapsed_str}")

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
        self.progress_bar.setValue(100 if result.success else self.progress_bar.value())

        status_text = "Download Complete" if result.success else ("Cancelled" if "cancelled" in str(result.error_message).lower() else "Failed")
        self.prog_status_label.setText(f"{status_text} ({result.downloaded_files} saved, {result.skipped_files} skipped)")

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

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure background threads are terminated safely on window close."""
        if self._download_worker is not None and self._download_worker.isRunning():
            self._download_worker.cancel()
            self._download_worker.wait(2000)
        if self._search_worker is not None and self._search_worker.isRunning():
            self._search_worker.cancel()
            self._search_worker.wait(1000)
        event.accept()


def main() -> None:
    """Entry point for the PySide6 Desktop GUI."""
    app = QApplication(sys.argv)
    app.setApplicationName("HikVision Downloader by Arivedha")
    app.setOrganizationName("Arivedha")
    app.setStyleSheet(DARK_THEME_QSS)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
