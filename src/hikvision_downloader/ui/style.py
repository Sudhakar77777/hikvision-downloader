"""Modern Dark Theme stylesheet adhering to the Arivedha brand palette."""

DARK_THEME_QSS: str = """
/* Global Window & Typography */
QWidget {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
    selection-background-color: #1E6B7B;
    selection-color: #FFFFFF;
}

QMainWindow {
    background-color: #0B0F19;
}

/* Header & Cards */
QFrame#headerFrame {
    background-color: #162032;
    border-bottom: 2px solid #1E6B7B;
    padding: 8px 16px;
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
QLineEdit, QSpinBox, QDateEdit, QTimeEdit, QComboBox {
    background-color: #162032;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F8FAFC;
    font-size: 13px;
}

QLineEdit:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QComboBox:focus {
    border: 1px solid #38BDF8;
    background-color: #1B273B;
}

QLineEdit:disabled, QSpinBox:disabled, QDateEdit:disabled, QComboBox:disabled {
    background-color: #0F172A;
    border-color: #1E293B;
    color: #64748B;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
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
    padding: 10px 24px;
    border-radius: 8px;
    letter-spacing: 0.5px;
}

QPushButton#primaryActionBtn:hover {
    background-color: #FF8A3D;
}

QPushButton#primaryActionBtn:pressed {
    background-color: #D95B0E;
}

QPushButton#primaryActionBtn:disabled {
    background-color: #33231B;
    color: #785A48;
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

/* Checkboxes */
QCheckBox {
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
    color: #38BDF8;
    font-family: "JetBrains Mono", "Fira Code", "SF Mono", Consolas, "Courier New", monospace;
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
