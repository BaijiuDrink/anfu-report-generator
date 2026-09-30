from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.project_history import RecentProject


class ProjectsPage(QWidget):
    openRequested = Signal(str)
    relocateRequested = Signal(str)
    removeRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._projects: list[RecentProject] = []
        self._build_ui()
        self.set_projects([])

    def _build_ui(self) -> None:
        self.setObjectName("projectsPage")
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 22)
        root.setSpacing(16)

        heading = QHBoxLayout()
        title = QLabel("项目管理")
        title.setObjectName("pageTitle")
        heading.addWidget(title)
        heading.addStretch(1)
        self.count_label = QLabel()
        self.count_label.setObjectName("projectCount")
        heading.addWidget(self.count_label)
        root.addLayout(heading)

        subtitle = QLabel(
            "从最近使用的项目继续工作，项目数据始终保存在原 JSON 文件中。"
        )
        subtitle.setObjectName("projectSubtitle")
        root.addWidget(subtitle)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索项目名称或 JSON 路径")
        root.addWidget(self.search_edit)

        self.empty_label = QLabel("暂无历史项目\n打开或保存项目后会显示在这里")
        self.empty_label.setObjectName("projectEmpty")
        self.empty_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.empty_label, 1)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("projectsList")
        self.list_widget.setSpacing(8)
        root.addWidget(self.list_widget, 1)

        actions = QHBoxLayout()
        self.remove_button = QPushButton("移除历史")
        self.remove_button.setToolTip("仅移除列表记录，不删除 JSON 文件")
        actions.addWidget(self.remove_button)
        actions.addStretch(1)
        self.relocate_button = QPushButton("重新定位")
        self.open_button = QPushButton("打开项目")
        self.open_button.setObjectName("primaryButton")
        actions.addWidget(self.relocate_button)
        actions.addWidget(self.open_button)
        root.addLayout(actions)

        self.search_edit.textChanged.connect(self._render)
        self.list_widget.currentItemChanged.connect(self._update_actions)
        self.list_widget.itemDoubleClicked.connect(
            lambda _item: self._emit(self.openRequested)
        )
        self.open_button.clicked.connect(lambda: self._emit(self.openRequested))
        self.relocate_button.clicked.connect(lambda: self._emit(self.relocateRequested))
        self.remove_button.clicked.connect(lambda: self._emit(self.removeRequested))

    def set_projects(self, projects: list[RecentProject]) -> None:
        self._projects = list(projects)
        self._render()

    def selected_record_id(self) -> str | None:
        item = self.list_widget.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _render(self) -> None:
        selected = self.selected_record_id()
        keyword = self.search_edit.text().casefold().strip()
        self.list_widget.clear()
        for project in self._projects:
            if keyword and keyword not in f"{project.name} {project.path}".casefold():
                continue
            status = " · JSON 文件已移动" if project.missing else ""
            opened = datetime.fromisoformat(project.last_opened).strftime(
                "%Y-%m-%d %H:%M"
            )
            item = QListWidgetItem(
                f"{project.name}{status}\n{project.path}\n最近打开 {opened}"
            )
            item.setData(Qt.UserRole, project.record_id)
            item.setData(Qt.UserRole + 1, project)
            item.setToolTip(str(project.path))
            item.setSizeHint(QSize(0, 86))
            self.list_widget.addItem(item)
            if project.record_id == selected:
                self.list_widget.setCurrentItem(item)
        self.count_label.setText(f"{len(self._projects)} 个项目")
        empty = self.list_widget.count() == 0
        self.empty_label.setText(
            "暂无历史项目\n打开或保存项目后会显示在这里"
            if not self._projects
            else "没有匹配的项目"
        )
        self.empty_label.setVisible(empty)
        self.list_widget.setVisible(not empty)
        if not empty and self.list_widget.currentItem() is None:
            self.list_widget.setCurrentRow(0)
        self._update_actions()

    def _update_actions(self, *_args) -> None:
        selected = self.selected_record_id() is not None
        self.open_button.setEnabled(selected)
        self.relocate_button.setEnabled(selected)
        self.remove_button.setEnabled(selected)

    def _emit(self, signal) -> None:
        record_id = self.selected_record_id()
        if record_id is not None:
            signal.emit(record_id)
