"""Modern Dark and Light Theme stylesheets adhering to the Arivedha brand palette."""

DARK_THEME_QSS: str = """
/* Global Window & Typography */
QWidget {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: ".AppleSystemUIFont", "SF Pro Text", "Segoe UI", "Helvetica Neue", Arial;
    font-size: 13px;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
}

QMainWindow {
    background-color: #0B0F19;
}

/* Header, Footer & Cards */
QFrame#headerFrame {
    background-color: #162032;
    border-bottom: 2px solid #1E6B7B;
    padding: 8px 12px;
}

QFrame#footerFrame {
    background-color: #0B0F19;
    border-top: 1px solid #1E293B;
    padding: 6px 16px;
}

QFrame#cardFrame {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px;
}

QGroupBox {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 24px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
    font-size: 12px;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #1E293B;
    color: #38BDF8;
}

/* Input Fields */
QLineEdit, QSpinBox, QDateEdit, QTimeEdit {
    background-color: #162032;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F8FAFC;
    font-size: 13px;
    min-height: 20px;
}

QComboBox {
    background-color: #162032;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 2px 4px 2px 8px;
    color: #F8FAFC;
    font-size: 13px;
    min-height: 24px;
}

QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QComboBox:focus {
    border: 1px solid #38BDF8;
    background-color: #1B273B;
}

QLineEdit:disabled, QSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled, QComboBox:disabled {
    background-color: #0F172A;
    border-color: #1E293B;
    color: #64748B;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #334155;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox QAbstractItemView {
    background-color: #162032;
    border: 1px solid #334155;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
    color: #F8FAFC;
}

/* Buttons */
QPushButton {
    background-color: #1E6B7B;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #258599;
}

QPushButton:pressed {
    background-color: #175461;
}

QPushButton:disabled {
    background-color: #1E293B;
    color: #64748B;
    border: 1px solid #334155;
}

/* Primary Action Button (Flame Orange) */
QPushButton#primaryActionBtn {
    background-color: #F37021;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 20px;
    border-radius: 6px;
    letter-spacing: 0.5px;
}

QPushButton#primaryActionBtn:hover {
    background-color: #E05D0D;
}

QPushButton#primaryActionBtn:pressed {
    background-color: #C24E05;
}

QPushButton#primaryActionBtn:disabled {
    background-color: #334155;
    color: #64748B;
    border: 1px solid #1E293B;
}

/* Abort / Destructive Button */
QPushButton#abortBtn {
    background-color: #DC2626;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 18px;
    border-radius: 6px;
}

QPushButton#abortBtn:hover {
    background-color: #EF4444;
}

QPushButton#abortBtn:pressed {
    background-color: #B91C1C;
}

QPushButton#abortBtn:disabled {
    background-color: #2D1B1E;
    color: #644248;
}

/* Secondary Ghost Button */
QPushButton#secondaryBtn {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid #475569;
}

QPushButton#secondaryBtn:hover {
    background-color: #334155;
    border-color: #64748B;
}

/* Quick Preset Button */
QPushButton#presetBtn {
    background-color: #162032;
    color: #94A3B8;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: 600;
    height: 26px;
}

QPushButton#presetBtn:hover {
    background-color: #1E293B;
    color: #38BDF8;
    border-color: #38BDF8;
}

/* Camera Row Widget */
QWidget#cameraRow {
    background-color: #162032;
    border: 1px solid #1E293B;
    border-radius: 4px;
    padding: 2px 4px;
}

QWidget#cameraRow:hover {
    background-color: #1E293B;
    border-color: #38BDF8;
}

/* Tables & Trees */
QTableView, QTreeView, QListWidget {
    background-color: #162032;
    alternate-background-color: #1B273B;
    border: 1px solid #334155;
    border-radius: 6px;
    gridline-color: #243247;
    color: #F8FAFC;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #1E293B;
    color: #94A3B8;
    padding: 6px 10px;
    border: none;
    border-right: 1px solid #334155;
    border-bottom: 2px solid #1E6B7B;
    font-weight: 600;
    font-size: 12px;
}

/* Progress Bar */
QProgressBar {
    background-color: #162032;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #F8FAFC;
    font-weight: 600;
    font-size: 12px;
    height: 20px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E6B7B, stop:1 #F37021);
    border-radius: 5px;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    spacing: 8px;
    color: #F8FAFC;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #162032;
}

QCheckBox::indicator:hover {
    border-color: #38BDF8;
}

QCheckBox::indicator:checked {
    background-color: #F37021;
    border-color: #F37021;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 1px solid #475569;
    background-color: #162032;
}

QRadioButton::indicator:hover {
    border-color: #38BDF8;
}

QRadioButton::indicator:checked {
    background-color: #162032;
    border: 5px solid #F37021;
}

/* Calendar Widget & Date Picker */
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #1E293B;
    border-bottom: 1px solid #334155;
}

QCalendarWidget QToolButton {
    color: #F8FAFC;
    background-color: #162032;
    border: 1px solid #334155;
    border-radius: 4px;
    margin: 2px;
    padding: 4px 8px;
    font-weight: 600;
}

QCalendarWidget QToolButton:hover {
    background-color: #1E6B7B;
    color: #FFFFFF;
}

QCalendarWidget QMenu {
    background-color: #162032;
    color: #F8FAFC;
    border: 1px solid #334155;
}

QCalendarWidget QSpinBox {
    background-color: #162032;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 4px;
}

QCalendarWidget QTableView {
    background-color: #0F172A;
    alternate-background-color: #162032;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
    color: #F8FAFC;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background-color: #162032;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background-color: #1E6B7B;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #F37021;
    border: 2px solid #FFFFFF;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background-color: #FF8A3D;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #0F172A;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0F172A;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #334155;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #475569;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Live Terminal Activity Console */
QPlainTextEdit#consoleLog {
    background-color: #0B0F19;
    color: #E2E8F0;
    font-family: "SF Mono", "JetBrains Mono", Consolas, "Courier New";
    font-size: 12px;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 8px;
}

/* Status Badges */
QLabel#statusBadge {
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 12px;
}
"""

LIGHT_THEME_QSS: str = """
/* Global Window & Typography */
QWidget {
    background-color: #F8FAFC;
    color: #0F172A;
    font-family: ".AppleSystemUIFont", "SF Pro Text", "Segoe UI", "Helvetica Neue", Arial;
    font-size: 13px;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
}

QMainWindow {
    background-color: #F1F5F9;
}

/* Header, Footer & Cards */
QFrame#headerFrame {
    background-color: #FFFFFF;
    border-bottom: 2px solid #1E6B7B;
    padding: 8px 12px;
}

QFrame#footerFrame {
    background-color: #F8FAFC;
    border-top: 1px solid #E2E8F0;
    padding: 6px 16px;
}

QFrame#cardFrame {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 12px;
}

QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    margin-top: 24px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
    font-size: 12px;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #FFFFFF;
    color: #1E6B7B;
}

/* Input Fields */
QLineEdit, QSpinBox, QDateEdit, QTimeEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0F172A;
    font-size: 13px;
    min-height: 20px;
}

QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 2px 4px 2px 8px;
    color: #0F172A;
    font-size: 13px;
    min-height: 24px;
}

QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QComboBox:focus {
    border: 1px solid #1E6B7B;
    background-color: #F0FDFA;
}

QLineEdit:disabled, QSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled, QComboBox:disabled {
    background-color: #F1F5F9;
    border-color: #E2E8F0;
    color: #94A3B8;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #CBD5E1;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
    color: #0F172A;
}

/* Buttons */
QPushButton {
    background-color: #1E6B7B;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #258599;
}

QPushButton:pressed {
    background-color: #175461;
}

QPushButton:disabled {
    background-color: #E2E8F0;
    color: #94A3B8;
    border: 1px solid #CBD5E1;
}

/* Primary Action Button (Flame Orange) */
QPushButton#primaryActionBtn {
    background-color: #F37021;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 20px;
    border-radius: 6px;
    letter-spacing: 0.5px;
}

QPushButton#primaryActionBtn:hover {
    background-color: #E05D0D;
}

QPushButton#primaryActionBtn:pressed {
    background-color: #C24E05;
}

QPushButton#primaryActionBtn:disabled {
    background-color: #94A3B8;
    color: #E2E8F0;
    border: 1px solid #CBD5E1;
}

/* Abort / Destructive Button */
QPushButton#abortBtn {
    background-color: #DC2626;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 18px;
    border-radius: 6px;
}

QPushButton#abortBtn:hover {
    background-color: #EF4444;
}

QPushButton#abortBtn:pressed {
    background-color: #B91C1C;
}

QPushButton#abortBtn:disabled {
    background-color: #FEE2E2;
    color: #991B1B;
}

/* Secondary Ghost Button */
QPushButton#secondaryBtn {
    background-color: #F1F5F9;
    color: #1E293B;
    border: 1px solid #CBD5E1;
}

QPushButton#secondaryBtn:hover {
    background-color: #E2E8F0;
    border-color: #94A3B8;
}

/* Quick Preset Button */
QPushButton#presetBtn {
    background-color: #F1F5F9;
    color: #475569;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: 600;
    height: 26px;
}

QPushButton#presetBtn:hover {
    background-color: #E2E8F0;
    color: #1E6B7B;
    border-color: #1E6B7B;
}

/* Camera Row Widget */
QWidget#cameraRow {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    padding: 2px 4px;
}

QWidget#cameraRow:hover {
    background-color: #F1F5F9;
    border-color: #1E6B7B;
}

/* Tables & Trees */
QTableView, QTreeView, QListWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    gridline-color: #E2E8F0;
    color: #0F172A;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #F1F5F9;
    color: #475569;
    padding: 6px 10px;
    border: none;
    border-right: 1px solid #CBD5E1;
    border-bottom: 2px solid #1E6B7B;
    font-weight: 600;
    font-size: 12px;
}

/* Progress Bar */
QProgressBar {
    background-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    text-align: center;
    color: #0F172A;
    font-weight: 600;
    font-size: 12px;
    height: 20px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E6B7B, stop:1 #F37021);
    border-radius: 5px;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    spacing: 8px;
    color: #0F172A;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #94A3B8;
    background-color: #FFFFFF;
}

QCheckBox::indicator:hover {
    border-color: #1E6B7B;
}

QCheckBox::indicator:checked {
    background-color: #F37021;
    border-color: #F37021;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 1px solid #94A3B8;
    background-color: #FFFFFF;
}

QRadioButton::indicator:hover {
    border-color: #1E6B7B;
}

QRadioButton::indicator:checked {
    background-color: #FFFFFF;
    border: 5px solid #F37021;
}

/* Calendar Widget & Date Picker */
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #F1F5F9;
    border-bottom: 1px solid #CBD5E1;
}

QCalendarWidget QToolButton {
    color: #0F172A;
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    margin: 2px;
    padding: 4px 8px;
    font-weight: 600;
}

QCalendarWidget QToolButton:hover {
    background-color: #1E6B7B;
    color: #FFFFFF;
}

QCalendarWidget QMenu {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
}

QCalendarWidget QSpinBox {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
}

QCalendarWidget QTableView {
    background-color: #FFFFFF;
    alternate-background-color: #F8FAFC;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
    color: #0F172A;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background-color: #E2E8F0;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background-color: #1E6B7B;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #F37021;
    border: 2px solid #FFFFFF;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background-color: #FF8A3D;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #F1F5F9;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #CBD5E1;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94A3B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #F1F5F9;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #CBD5E1;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #94A3B8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Live Terminal Activity Console */
QPlainTextEdit#consoleLog {
    background-color: #0F172A;
    color: #E2E8F0;
    font-family: "SF Mono", "JetBrains Mono", Consolas, "Courier New";
    font-size: 12px;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px;
}

/* Status Badges */
QLabel#statusBadge {
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 12px;
}
"""
