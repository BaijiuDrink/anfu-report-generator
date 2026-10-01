LIGHT_WORKSTATION_QSS = """
QWidget {
    color: #202730;
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
}
QMainWindow, QWidget#applicationRoot {
    background: #f6f4ee;
}
QFrame#topBar {
    background: #fdfcf9;
    border-bottom: 1px solid #dddbd5;
}
QLabel#brandTitle {
    color: #202730;
    font-family: "Microsoft YaHei UI";
    font-size: 19px;
    font-weight: 700;
}
QLabel#brandSubtitle {
    color: #7b8187;
    font-size: 11px;
}
QFrame#sidebar {
    background: #fdfcf9;
    border-right: 1px solid #dddbd5;
}
QFrame#sidebar QLabel {
    color: #7b8187;
}
QFrame#sidebar QPushButton {
    color: #535961;
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 9px 10px;
    text-align: left;
    font-weight: 600;
}
QFrame#sidebar QPushButton:hover {
    background: #f0eee8;
}
QFrame#sidebar QPushButton:checked {
    color: #22436c;
    background: #e1ecfb;
}
QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QListView, QListWidget, QComboBox {
    background: #fdfcf9;
    border: 1px solid #c0bdb7;
    border-radius: 6px;
    padding: 7px;
    selection-background-color: #e1ecfb;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QListView:focus, QListWidget:focus, QComboBox:focus {
    border: 1px solid #365987;
}
QPushButton {
    background: #fdfcf9;
    border: 1px solid #c0bdb7;
    border-radius: 6px;
    padding: 7px 12px;
    font-weight: 500;
}
QPushButton:hover {
    background: #f0eee8;
}
QPushButton:disabled {
    color: #9b9d9e;
    background: #f0eee8;
}
QPushButton#primaryButton {
    color: #ffffff;
    background: #365987;
    border-color: #365987;
}
QPushButton#primaryButton:hover {
    background: #22436c;
}
QGroupBox {
    background: #fdfcf9;
    border: 1px solid #dddbd5;
    border-radius: 8px;
    margin-top: 14px;
    padding: 8px 12px 12px 12px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}
QListView::item, QListWidget::item {
    border-bottom: 1px solid #f0eee8;
    padding: 10px 8px;
}
QListView::item:selected, QListWidget::item:selected {
    color: #22436c;
    background: #e1ecfb;
    border-left: 3px solid #365987;
}
QLabel#pageTitle, QLabel#pageSectionTitle {
    color: #202730;
    font-size: 18px;
    font-weight: 700;
}
QScrollBar:vertical {
    background: #f0eee8;
    width: 9px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #c0bdb7;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QStatusBar {
    background: #fdfcf9;
    color: #7b8187;
    border-top: 1px solid #dddbd5;
}
QLabel#navLabel, QLabel#sideFoot, QLabel#listCount, QLabel#editorMeta, QLabel#editorHint {
    color: #7b8187;
    font-size: 11px;
}
QLabel#sideFoot {
    border-top: 1px solid #dddbd5;
    padding: 12px 4px 2px 4px;
}
QLabel#saveState {
    color: #007047;
    background: #f0eee8;
    border: 1px solid #dddbd5;
    border-radius: 12px;
    padding: 5px 10px;
    font-size: 11px;
}
QLabel#saveState[dirty="true"] {
    color: #b67700;
}
QFrame#findingsPanel {
    background: #fdfcf9;
    border-right: 1px solid #dddbd5;
}
QFrame#editorPanel, QWidget#editorCanvas, QScrollArea#editorScroll {
    background: #f6f4ee;
    border: none;
}
QWidget#editorHeader, QFrame#editorFoot {
    background: #fdfcf9;
    border-bottom: 1px solid #dddbd5;
}
QFrame#editorFoot {
    border-bottom: none;
    border-top: 1px solid #dddbd5;
}
QLabel#editorTitle {
    font-family: "Microsoft YaHei UI";
    font-size: 18px;
    font-weight: 600;
}
QLabel#fieldLabel {
    color: #535961;
    font-size: 12px;
}
QPushButton#filterChip {
    color: #535961;
    background: #f0eee8;
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 3px 8px;
    font-size: 11px;
}
QPushButton#filterChip:hover {
    border-color: #c0bdb7;
}
QPushButton#filterChip:checked {
    color: #fdfcf9;
    background: #202730;
}
QListView#findingsList {
    border: none;
    background: #fdfcf9;
    padding: 2px 0;
}
QListView#findingsList::item {
    border: none;
    padding: 0;
}
QListView#findingsList::item:selected {
    background: #fdfcf9;
}
QPushButton#riskChoice, QPushButton#pillChoice {
    color: #535961;
    background: #fdfcf9;
    border: 1px solid #c0bdb7;
    border-radius: 12px;
    padding: 5px 9px;
    font-size: 12px;
}
QPushButton#riskChoice:checked, QPushButton#pillChoice:checked {
    color: #22436c;
    background: #e1ecfb;
    border-color: #365987;
}
QGroupBox {
    color: #202730;
}
QGroupBox QPlainTextEdit, QGroupBox QTextEdit {
    line-height: 1.5;
}
QSplitter::handle {
    background: #dddbd5;
    width: 1px;
}
QListWidget#libraryList, QTextBrowser#libraryPreview {
    background: #fdfcf9;
    border: 1px solid #dddbd5;
    border-radius: 8px;
}
QListWidget#libraryList::item {
    padding: 10px;
}
QWidget#projectsPage {
    background: #f6f4ee;
}
QLabel#projectSubtitle, QLabel#projectCount {
    color: #7b8187;
    font-size: 12px;
}
QLabel#projectEmpty {
    color: #7b8187;
    background: #fdfcf9;
    border: 1px dashed #c0bdb7;
    border-radius: 8px;
    padding: 30px;
}
QListWidget#projectsList {
    background: #f6f4ee;
    border: none;
    padding: 0;
}
QListWidget#projectsList::item {
    color: #535961;
    background: #fdfcf9;
    border: 1px solid #dddbd5;
    border-radius: 8px;
    padding: 12px 16px;
}
QListWidget#projectsList::item:hover {
    background: #f8f7f3;
}
QListWidget#projectsList::item:selected {
    color: #22436c;
    background: #e1ecfb;
    border: 1px solid #365987;
}
"""
