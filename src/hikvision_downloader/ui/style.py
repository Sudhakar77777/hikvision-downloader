"""Modern Dark and Light Theme stylesheets adhering to the Arivedha brand palette."""

DARK_THEME_QSS: str = """
/* Global Window & Base Rules */
QWidget {
    background-color: #0F172A;
    color: #F8FAFC;
    font-size: 13px;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
}

QMainWindow {
    background-color: #0B0F19;
}

/* Text Labels: completely flat text by default */
QLabel {
    background: transparent;
    border: none;
    padding: 0px;
    color: #F8FAFC;
}

/* Header, Footer & Frames */
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

QFrame#downloadSettingsFrame {
    background-color: #162032;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 12px;
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
    padding: 4px 8px;
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

QDateEdit::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 32px;
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
    padding: 6px 14px;
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

/* Connect / Disconnect State Button */
QPushButton#connectBtn {
    background-color: #1E6B7B;
    color: #FFFFFF;
    font-weight: bold;
    border-radius: 6px;
    padding: 4px 12px;
    min-height: 24px;
}

QPushButton#connectBtn:hover {
    background-color: #258599;
}

QPushButton#connectBtn[connected="true"] {
    background-color: #DC2626;
    color: #FFFFFF;
}

QPushButton#connectBtn[connected="true"]:hover {
    background-color: #EF4444;
}

/* Search Action Button */
QPushButton#searchBtn {
    background-color: #1E6B7B;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 16px;
    border-radius: 6px;
    min-height: 32px;
}

QPushButton#searchBtn:hover {
    background-color: #258599;
}

QPushButton#searchBtn:disabled {
    background-color: #1E293B;
    color: #64748B;
    border: 1px solid #334155;
}

/* Primary Action Button (Flame Orange) */
QPushButton#primaryActionBtn, QPushButton#downloadBtn {
    background-color: #F37021;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 16px;
    border-radius: 6px;
    letter-spacing: 0.3px;
    min-height: 32px;
}

QPushButton#primaryActionBtn:hover, QPushButton#downloadBtn:hover {
    background-color: #E05D0D;
}

QPushButton#primaryActionBtn:pressed, QPushButton#downloadBtn:pressed {
    background-color: #C24E05;
}

QPushButton#primaryActionBtn:disabled, QPushButton#downloadBtn:disabled {
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
    padding: 8px 16px;
    border-radius: 6px;
    min-height: 32px;
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
    padding: 4px 10px;
    min-height: 24px;
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

/* Compact Tool Buttons (e.g. Folder Browse) */
QToolButton#browseBtn {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #475569;
    border-radius: 4px;
    padding: 0px;
    font-size: 13px;
}

QToolButton#browseBtn:hover {
    background-color: #334155;
    border-color: #38BDF8;
}

/* Camera Row Widget */
QWidget#cameraRow {
    background-color: #162032;
    border: 1px solid #1E293B;
    border-radius: 4px;
    padding: 1px 4px;
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
    font-weight: 700;
    font-size: 13px;
    border: none;
    border-right: 1px solid #334155;
    border-bottom: 2px solid #1E6B7B;
}

QHeaderView::section:vertical {
    background-color: #1E293B;
    color: #64748B;
    font-size: 11px;
    font-weight: 600;
    padding: 0 4px;
    border: none;
    border-right: 1px solid #334155;
    border-bottom: 1px solid #243247;
}

QHeaderView::section:hover {
    background-color: #273549;
    color: #F8FAFC;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    spacing: 6px;
    color: #F8FAFC;
    font-size: 13px;
    background: transparent;
    border: none;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #475569;
    border-radius: 4px;
    background-color: #162032;
}

QCheckBox::indicator:hover {
    border-color: #38BDF8;
}

QCheckBox::indicator:checked {
    background-color: #1E6B7B;
    border-color: #38BDF8;
    image: none;
}

QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #475569;
    border-radius: 7px;
    background-color: #162032;
}

QRadioButton::indicator:hover {
    border-color: #38BDF8;
}

QRadioButton::indicator:checked {
    background-color: #F37021;
    border: 2px solid #FFFFFF;
    border-radius: 7px;
}

/* Progress Bars */
QProgressBar {
    background-color: #162032;
    border: 1px solid #334155;
    border-radius: 4px;
    text-align: center;
    color: #FFFFFF;
    font-weight: 600;
    font-size: 10px;
    height: 10px;
}

QProgressBar::chunk {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #F37021,
        stop: 1 #FF853E
    );
    border-radius: 3px;
}

/* Horizontal Sliders */
QSlider::groove:horizontal {
    border: 1px solid #334155;
    height: 6px;
    background-color: #162032;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background-color: #1E6B7B;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #38BDF8;
    border: 2px solid #0F172A;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background-color: #7DD3FC;
    transform: scale(1.1);
}

/* Scroll Bars */
QScrollBar:vertical {
    border: none;
    background-color: #0F172A;
    width: 10px;
    margin: 0px;
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
    border: none;
    background-color: #0F172A;
    height: 10px;
    margin: 0px;
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
    font-size: 12px;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 8px;
}

/* Status & Space Badges */
QLabel#statusBadge {
    height: 28px;
    line-height: 28px;
    padding: 2px 8px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 11px;
}

QLabel#spaceBadge {
    padding: 2px 8px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 11px;
}

/* Calendar Widget */
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #162032;
    border-bottom: 1px solid #334155;
}

QCalendarWidget QToolButton,
#qt_calendar_prevmonth,
#qt_calendar_nextmonth {
    color: #F8FAFC;
    background-color: #334155;
    border: 1px solid #475569;
    border-radius: 4px;
    margin: 2px;
    padding: 2px 6px;
    font-weight: 600;
}

QCalendarWidget QToolButton:hover,
#qt_calendar_prevmonth:hover,
#qt_calendar_nextmonth:hover {
    background-color: #1E6B7B;
    border-color: #38BDF8;
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
}

QCalendarWidget QTableView {
    background-color: #0F172A;
    color: #F8FAFC;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
}
"""

LIGHT_THEME_QSS: str = """
/* Global Window & Base Rules */
QWidget {
    background-color: #ECEFF3;
    color: #1E293B;
    font-size: 13px;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
}

QMainWindow {
    background-color: #ECEFF3;
}

/* Text Labels: completely flat text by default */
QLabel {
    background: transparent;
    border: none;
    padding: 0px;
    color: #1E293B;
}

/* Header, Footer & Frames */
QFrame#headerFrame {
    background-color: #E2E8F0;
    border-bottom: 2px solid #1E6B7B;
    padding: 8px 12px;
}

QFrame#footerFrame {
    background-color: #E2E8F0;
    border-top: 1px solid #CBD5E1;
    padding: 6px 16px;
}

QFrame#cardFrame {
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 12px;
}

QFrame#downloadSettingsFrame {
    background-color: #F1F5F9;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px 12px;
}

QGroupBox {
    background-color: #F8FAFC;
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
    background-color: #F8FAFC;
    color: #0284C7;
}

/* Input Fields */
QLineEdit, QSpinBox, QDateEdit, QTimeEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px 8px;
    color: #1E293B;
    font-size: 13px;
    min-height: 20px;
}

QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 2px 4px 2px 8px;
    color: #1E293B;
    font-size: 13px;
    min-height: 24px;
}

QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QComboBox:focus {
    border: 1px solid #0284C7;
    background-color: #FFFFFF;
}

QLineEdit:disabled, QSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled, QComboBox:disabled {
    background-color: #E2E8F0;
    border-color: #CBD5E1;
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

QDateEdit::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 32px;
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
    padding: 6px 14px;
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

/* Connect / Disconnect State Button */
QPushButton#connectBtn {
    background-color: #1E6B7B;
    color: #FFFFFF;
    font-weight: bold;
    border-radius: 6px;
    padding: 4px 12px;
    min-height: 24px;
}

QPushButton#connectBtn:hover {
    background-color: #258599;
}

QPushButton#connectBtn[connected="true"] {
    background-color: #DC2626;
    color: #FFFFFF;
}

QPushButton#connectBtn[connected="true"]:hover {
    background-color: #EF4444;
}

/* Search Action Button */
QPushButton#searchBtn {
    background-color: #1E6B7B;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 16px;
    border-radius: 6px;
    min-height: 32px;
}

QPushButton#searchBtn:hover {
    background-color: #258599;
}

QPushButton#searchBtn:disabled {
    background-color: #E2E8F0;
    color: #94A3B8;
    border: 1px solid #CBD5E1;
}

/* Primary Action Button (Flame Orange) */
QPushButton#primaryActionBtn, QPushButton#downloadBtn {
    background-color: #F37021;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 16px;
    border-radius: 6px;
    letter-spacing: 0.3px;
    min-height: 32px;
}

QPushButton#primaryActionBtn:hover, QPushButton#downloadBtn:hover {
    background-color: #E05D0D;
}

QPushButton#primaryActionBtn:pressed, QPushButton#downloadBtn:pressed {
    background-color: #C24E05;
}

QPushButton#primaryActionBtn:disabled, QPushButton#downloadBtn:disabled {
    background-color: #E2E8F0;
    color: #94A3B8;
    border: 1px solid #CBD5E1;
}

/* Abort / Destructive Button */
QPushButton#abortBtn {
    background-color: #DC2626;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 6px;
    min-height: 32px;
}

QPushButton#abortBtn:hover {
    background-color: #EF4444;
}

QPushButton#abortBtn:pressed {
    background-color: #B91C1C;
}

QPushButton#abortBtn:disabled {
    background-color: #FEE2E2;
    color: #FCA5A5;
}

/* Secondary Ghost Button */
QPushButton#secondaryBtn {
    background-color: #E2E8F0;
    color: #334155;
    border: 1px solid #CBD5E1;
    padding: 4px 10px;
    min-height: 24px;
}

QPushButton#secondaryBtn:hover {
    background-color: #CBD5E1;
    border-color: #94A3B8;
}

/* Quick Preset Button */
QPushButton#presetBtn {
    background-color: #E2E8F0;
    color: #475569;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: 600;
    height: 26px;
}

QPushButton#presetBtn:hover {
    background-color: #CBD5E1;
    color: #0284C7;
    border-color: #0284C7;
}

/* Compact Tool Buttons (e.g. Folder Browse) */
QToolButton#browseBtn {
    background-color: #E2E8F0;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    padding: 0px;
    font-size: 13px;
}

QToolButton#browseBtn:hover {
    background-color: #CBD5E1;
    border-color: #0284C7;
}

/* Camera Row Widget */
QWidget#cameraRow {
    background-color: #F1F5F9;
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    padding: 1px 4px;
}

QWidget#cameraRow:hover {
    background-color: #E2E8F0;
    border-color: #0284C7;
}

/* Tables & Trees */
QTableView, QTreeView, QListWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    gridline-color: #E2E8F0;
    color: #1E293B;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #E2E8F0;
    color: #475569;
    padding: 6px 10px;
    font-weight: 700;
    font-size: 13px;
    border: none;
    border-right: 1px solid #CBD5E1;
    border-bottom: 2px solid #1E6B7B;
}

QHeaderView::section:vertical {
    background-color: #E2E8F0;
    color: #64748B;
    font-size: 11px;
    font-weight: 600;
    padding: 0 4px;
    border: none;
    border-right: 1px solid #CBD5E1;
    border-bottom: 1px solid #CBD5E1;
}

QHeaderView::section:hover {
    background-color: #CBD5E1;
    color: #0F172A;
}

/* Checkboxes & Radio Buttons */
QCheckBox, QRadioButton {
    spacing: 6px;
    color: #0F172A;
    font-size: 13px;
    background: transparent;
    border: none;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #94A3B8;
    border-radius: 4px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:hover {
    border-color: #0284C7;
}

QCheckBox::indicator:checked {
    background-color: #1E6B7B;
    border-color: #0284C7;
    image: none;
}

QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #94A3B8;
    border-radius: 7px;
    background-color: #FFFFFF;
}

QRadioButton::indicator:hover {
    border-color: #0284C7;
}

QRadioButton::indicator:checked {
    background-color: #F37021;
    border: 2px solid #0F172A;
    border-radius: 7px;
}

/* Progress Bars */
QProgressBar {
    background-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    text-align: center;
    color: #0F172A;
    font-weight: 600;
    font-size: 10px;
    height: 10px;
}

QProgressBar::chunk {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #F37021,
        stop: 1 #FF853E
    );
    border-radius: 3px;
}

/* Horizontal Sliders */
QSlider::groove:horizontal {
    border: 1px solid #CBD5E1;
    height: 6px;
    background-color: #E2E8F0;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background-color: #1E6B7B;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #0284C7;
    border: 2px solid #FFFFFF;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background-color: #38BDF8;
}

/* Scroll Bars */
QScrollBar:vertical {
    border: none;
    background-color: #F8FAFC;
    width: 10px;
    margin: 0px;
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
    border: none;
    background-color: #F8FAFC;
    height: 10px;
    margin: 0px;
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
    background-color: #1E293B;
    color: #F1F5F9;
    font-size: 12px;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px;
}

/* Status & Space Badges */
QLabel#statusBadge {
    height: 28px;
    line-height: 28px;
    padding: 2px 8px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 11px;
}

QLabel#spaceBadge {
    padding: 2px 8px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 11px;
}

/* Calendar Widget */
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #E2E8F0;
    border-bottom: 1px solid #CBD5E1;
}

QCalendarWidget QToolButton,
#qt_calendar_prevmonth,
#qt_calendar_nextmonth {
    color: #1E293B;
    background-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    margin: 2px;
    padding: 2px 6px;
    font-weight: 600;
}

QCalendarWidget QToolButton:hover,
#qt_calendar_prevmonth:hover,
#qt_calendar_nextmonth:hover {
    background-color: #CBD5E1;
    border-color: #0284C7;
}

QCalendarWidget QMenu {
    background-color: #FFFFFF;
    color: #1E293B;
    border: 1px solid #CBD5E1;
}

QCalendarWidget QSpinBox {
    background-color: #FFFFFF;
    color: #1E293B;
    border: 1px solid #CBD5E1;
}

QCalendarWidget QTableView {
    background-color: #FFFFFF;
    color: #1E293B;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
}
"""
