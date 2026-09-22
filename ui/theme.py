LIGHT_WORKSTATION_QSS = """
QWidget {
    color: #172033;
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
}
QMainWindow, QWidget#applicationRoot {
    background: #f4f7fb;
}
QFrame#topBar {
    background: #ffffff;
    border-bottom: 1px solid #dce3ed;
}
QLabel#brandTitle {
    color: #10233f;
    font-size: 20px;
    font-weight: 700;
}
QLabel#brandSubtitle {
    color: #738096;
    font-size: 11px;
}
QFrame#sidebar {
    background: #14243c;
    border: none;
}
QFrame#sidebar QLabel {
    color: #91a2b9;
}
QFrame#sidebar QPushButton {
    color: #dce5f2;
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 11px 14px;
    text-align: left;
    font-weight: 600;
}
QFrame#sidebar QPushButton:hover {
    background: #1d3557;
}
QFrame#sidebar QPushButton:checked {
    color: #ffffff;
    background: #2563eb;
}
QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QListView, QListWidget, QComboBox {
    background: #ffffff;
    border: 1px solid #cfd8e6;
    border-radius: 6px;
    padding: 7px;
    selection-background-color: #2563eb;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QListView:focus, QListWidget:focus, QComboBox:focus {
    border: 1px solid #2563eb;
}
QPushButton {
    background: #eef2f7;
    border: 1px solid #d8e0eb;
    border-radius: 6px;
    padding: 8px 13px;
    font-weight: 600;
}
QPushButton:hover {
    background: #e3e9f2;
}
QPushButton:disabled {
    color: #9aa6b6;
    background: #f2f4f7;
}
QPushButton#primaryButton {
    color: #ffffff;
    background: #2563eb;
    border-color: #2563eb;
}
QPushButton#primaryButton:hover {
    background: #1d4ed8;
}
QGroupBox {
    background: #ffffff;
    border: 1px solid #dce3ed;
    border-radius: 8px;
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
}
QListView::item, QListWidget::item {
    border-bottom: 1px solid #edf1f6;
    padding: 10px 8px;
}
QListView::item:selected, QListWidget::item:selected {
    color: #15366b;
    background: #dbeafe;
    border-left: 3px solid #2563eb;
}
QLabel#pageTitle, QLabel#pageSectionTitle {
    color: #10233f;
    font-size: 18px;
    font-weight: 700;
}
QScrollBar:vertical {
    background: #eef2f7;
    width: 11px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #b6c1d0;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QStatusBar {
    background: #ffffff;
    color: #657289;
    border-top: 1px solid #dce3ed;
}
"""
