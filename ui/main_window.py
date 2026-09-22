from __future__ import annotations

import logging
import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app_state import ProjectState
from services.project_store import ProjectStore
from services.report_service import ReportService, ReportValidationError
from ui.pages.findings_page import FindingsPage
from ui.pages.library_page import LibraryPage
from ui.theme import LIGHT_WORKSTATION_QSS
from vuln_manager import VulnManager

LOGGER = logging.getLogger(__name__)


def default_screenshot_directory() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return root / "BaijiuDrink" / "AnfuReportWorkbench" / "screenshots"


class MainWindow(QMainWindow):
    def __init__(
        self,
        state: ProjectState | None = None,
        project_store: ProjectStore | None = None,
        report_service: ReportService | None = None,
        vuln_manager: VulnManager | None = None,
        screenshots_dir: Path | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.state = state or ProjectState()
        self.project_store = project_store or ProjectStore()
        self.report_service = report_service or ReportService()
        self.vuln_manager = vuln_manager or VulnManager()
        self.screenshots_dir = Path(screenshots_dir or default_screenshot_directory())
        self._syncing_project_name = False
        self.setWindowTitle("安服报告工作台")
        self.resize(1440, 900)
        self.setMinimumSize(1080, 680)
        self.setStyleSheet(LIGHT_WORKSTATION_QSS)
        self._build_ui()
        self._refresh_from_state()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("applicationRoot")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 14, 20, 14)
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(1)
        brand = QLabel("安服报告工作台")
        brand.setObjectName("brandTitle")
        subtitle = QLabel("漏洞整理、证据归档与规范报告生成")
        subtitle.setObjectName("brandSubtitle")
        brand_layout.addWidget(brand)
        brand_layout.addWidget(subtitle)
        top_layout.addLayout(brand_layout)
        top_layout.addSpacing(28)
        project_label = QLabel("当前项目")
        top_layout.addWidget(project_label)
        self.project_name_edit = QLineEdit()
        self.project_name_edit.setPlaceholderText("请输入项目名称")
        self.project_name_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_layout.addWidget(self.project_name_edit, 1)
        self.new_button = QPushButton("新建")
        self.open_button = QPushButton("打开")
        self.save_button = QPushButton("保存")
        self.generate_button = QPushButton("生成报告")
        self.generate_button.setObjectName("primaryButton")
        for button in (
            self.new_button,
            self.open_button,
            self.save_button,
            self.generate_button,
        ):
            top_layout.addWidget(button)
        root.addWidget(top_bar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 20, 14, 20)
        section = QLabel("工作区")
        sidebar_layout.addWidget(section)
        self.findings_nav = QPushButton("漏洞管理")
        self.findings_nav.setCheckable(True)
        self.library_nav = QPushButton("漏洞库")
        self.library_nav.setCheckable(True)
        sidebar_layout.addWidget(self.findings_nav)
        sidebar_layout.addWidget(self.library_nav)
        sidebar_layout.addStretch(1)
        version = QLabel("PySide6 Desktop")
        sidebar_layout.addWidget(version)
        body_layout.addWidget(sidebar)

        self.page_stack = QStackedWidget()
        self.findings_page = FindingsPage(self.screenshots_dir, self.vuln_manager)
        self.library_page = LibraryPage(self.vuln_manager)
        self.page_stack.addWidget(self.findings_page)
        self.page_stack.addWidget(self.library_page)
        body_layout.addWidget(self.page_stack, 1)
        root.addWidget(body, 1)

        self.project_name_edit.textEdited.connect(self._project_name_changed)
        self.new_button.clicked.connect(self.new_project)
        self.open_button.clicked.connect(self.open_project)
        self.save_button.clicked.connect(self.save_project)
        self.generate_button.clicked.connect(self.generate_report)
        self.findings_nav.clicked.connect(self.show_findings_page)
        self.library_nav.clicked.connect(self.show_library_page)
        self.findings_page.stateChanged.connect(self._on_state_changed)
        self.show_findings_page()
        self.statusBar().showMessage("就绪")

    def _refresh_from_state(self) -> None:
        self._syncing_project_name = True
        try:
            self.project_name_edit.setText(self.state.project_name)
        finally:
            self._syncing_project_name = False
        self.findings_page.set_state(self.state)

    def _project_name_changed(self, text: str) -> None:
        if self._syncing_project_name:
            return
        self.state.project_name = text
        self.state.mark_dirty()
        self._on_state_changed()

    def _on_state_changed(self) -> None:
        suffix = (
            " *" if self.state.dirty or self.findings_page.editor.is_dirty() else ""
        )
        self.setWindowTitle(f"安服报告工作台{suffix}")

    def show_findings_page(self) -> bool:
        self.page_stack.setCurrentWidget(self.findings_page)
        self.findings_nav.setChecked(True)
        self.library_nav.setChecked(False)
        return True

    def show_library_page(self) -> bool:
        if self.findings_page.editor.is_dirty():
            decision = self.findings_page.confirm_unsaved()
            if decision == "cancel":
                self.findings_nav.setChecked(True)
                self.library_nav.setChecked(False)
                return False
            if decision == "save" and not self.findings_page.save_current():
                return False
            if decision == "discard":
                index = self.findings_page.current_index
                if index is None:
                    self.findings_page.editor.clear_form()
                else:
                    self.findings_page.editor.set_finding(self.state.findings[index])
        self.library_page.refresh()
        self.page_stack.setCurrentWidget(self.library_page)
        self.findings_nav.setChecked(False)
        self.library_nav.setChecked(True)
        return True

    def confirm_project_change(self) -> str:
        if not self.state.dirty and not self.findings_page.editor.is_dirty():
            return "discard"
        box = QMessageBox(self)
        box.setWindowTitle("未保存的更改")
        box.setText("当前项目存在未保存内容。")
        save = box.addButton("保存", QMessageBox.AcceptRole)
        discard = box.addButton("放弃", QMessageBox.DestructiveRole)
        box.addButton("取消", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is save:
            return "save"
        if box.clickedButton() is discard:
            return "discard"
        return "cancel"

    def _allow_project_change(self) -> bool:
        decision = self.confirm_project_change()
        if decision == "cancel":
            return False
        if decision == "save":
            return self.save_project()
        return True

    def new_project(self) -> bool:
        if not self._allow_project_change():
            return False
        self.state.clear()
        self._refresh_from_state()
        self.show_findings_page()
        self.statusBar().showMessage("已新建空白项目", 4000)
        return True

    def open_project(self, path: Path | None = None) -> bool:
        if not self._allow_project_change():
            return False
        if path is None or isinstance(path, bool):
            selected, _ = QFileDialog.getOpenFileName(
                self, "打开项目", "", "项目文件 (*.json);;所有文件 (*)"
            )
            if not selected:
                return False
            path = Path(selected)
        try:
            loaded = self.project_store.load(Path(path))
        except Exception:
            LOGGER.exception("Failed to open project: %s", path)
            QMessageBox.critical(self, "无法打开项目", "项目文件无法读取或格式不正确。")
            return False
        self.state.replace(loaded.project_name, loaded.findings, loaded.path)
        self._refresh_from_state()
        self.show_findings_page()
        self.statusBar().showMessage(
            f"已打开项目，共 {len(self.state.findings)} 条漏洞", 5000
        )
        return True

    def save_project(self, path: Path | None = None) -> bool:
        if not self.findings_page.commit_active():
            return False
        if not self.state.findings:
            QMessageBox.warning(self, "无法保存", "没有可保存的漏洞记录")
            return False
        if path is None or isinstance(path, bool):
            path = self.state.project_path
        if path is None:
            selected, _ = QFileDialog.getSaveFileName(
                self, "保存项目", "project.json", "项目文件 (*.json)"
            )
            if not selected:
                return False
            path = Path(selected)
        path = Path(path)
        project_name = self.project_name_edit.text().strip()
        try:
            self.project_store.save(path, project_name, self.state.findings)
        except Exception:
            LOGGER.exception("Failed to save project: %s", path)
            QMessageBox.critical(
                self, "无法保存项目", "项目文件写入失败，请检查路径和权限。"
            )
            self.state.mark_dirty()
            return False
        self.state.project_name = project_name
        self.state.project_path = path.resolve()
        self.state.mark_clean()
        self.findings_page.editor.mark_clean()
        self._on_state_changed()
        self.statusBar().showMessage(f"项目已保存：{path}", 5000)
        return True

    def generate_report(self, path: Path | None = None) -> bool:
        if not self.findings_page.commit_active():
            return False
        base_dir = self.state.project_path.parent if self.state.project_path else None
        try:
            check = self.report_service.check(self.state.findings, base_dir)
        except ReportValidationError as exc:
            QMessageBox.warning(self, "无法生成报告", str(exc))
            return False
        if check.missing_images:
            paths = "\n".join(str(item) for item in check.missing_images[:8])
            if len(check.missing_images) > 8:
                paths += f"\n另有 {len(check.missing_images) - 8} 个文件"
            answer = QMessageBox.question(
                self,
                "证据图片缺失",
                f"以下证据图片无法读取：\n\n{paths}\n\n是否继续生成报告？",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if answer != QMessageBox.Yes:
                return False
        project_name = self.project_name_edit.text().strip() or "渗透测试报告"
        if path is None or isinstance(path, bool):
            selected, _ = QFileDialog.getSaveFileName(
                self,
                "生成报告",
                f"{project_name}_渗透测试报告.docx",
                "Word 文档 (*.docx)",
            )
            if not selected:
                return False
            path = Path(selected)
        try:
            self.report_service.generate(
                project_name, self.state.findings, Path(path), base_dir
            )
        except Exception:
            LOGGER.exception("Failed to generate report: %s", path)
            QMessageBox.critical(self, "报告生成失败", "无法写入报告，请检查输出路径。")
            return False
        self.statusBar().showMessage(f"报告已生成：{path}", 7000)
        return True

    def closeEvent(self, event) -> None:
        decision = self.confirm_project_change()
        if decision == "cancel":
            event.ignore()
            return
        if decision == "save" and not self.save_project():
            event.ignore()
            return
        event.accept()
