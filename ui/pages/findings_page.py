from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app_state import ProjectState
from ui.dialogs.batch_add_dialog import BatchAddDialog
from ui.dialogs.library_picker import LibraryPicker
from ui.widgets.finding_editor import FindingEditor, FindingValidationError
from vuln_manager import create_finding


class FindingsListModel(QAbstractListModel):
    def __init__(self, state: ProjectState | None = None, parent=None):
        super().__init__(parent)
        self.state = state or ProjectState()
        self.search_text = ""
        self._visible_indices: list[int] = []
        self.refresh()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._visible_indices)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._visible_indices):
            return None
        finding = self.state.findings[self._visible_indices[index.row()]]
        if role == Qt.DisplayRole:
            name = finding.get("name") or "未命名漏洞"
            risk = finding.get("risk_level") or "中危"
            address = (
                (finding.get("url") or "").splitlines()[0]
                if finding.get("url")
                else "未填写地址"
            )
            zone = finding.get("network_zone") or "互联网"
            return f"{name}\n{risk} · {zone} · {address}"
        if role == Qt.UserRole:
            return self._visible_indices[index.row()]
        return None

    def refresh(self) -> None:
        self.beginResetModel()
        keyword = self.search_text.casefold().strip()
        self._visible_indices = []
        for index, finding in enumerate(self.state.findings):
            searchable = " ".join(
                str(finding.get(key, "")) for key in ("name", "url", "network_zone")
            ).casefold()
            if not keyword or keyword in searchable:
                self._visible_indices.append(index)
        self.endResetModel()

    def set_state(self, state: ProjectState) -> None:
        self.state = state
        self.refresh()

    def set_search_text(self, text: str) -> None:
        self.search_text = text
        self.refresh()

    def finding_index(self, row: int) -> int | None:
        if 0 <= row < len(self._visible_indices):
            return self._visible_indices[row]
        return None

    def row_for_finding(self, finding_index: int) -> int | None:
        try:
            return self._visible_indices.index(finding_index)
        except ValueError:
            return None


class FindingsPage(QWidget):
    stateChanged = Signal()
    addFromLibraryRequested = Signal()

    def __init__(self, screenshots_dir: Path, vuln_manager, parent=None):
        super().__init__(parent)
        self.screenshots_dir = Path(screenshots_dir)
        self.vuln_manager = vuln_manager
        self.state = ProjectState()
        self.current_index: int | None = None
        self._syncing_selection = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter)

        left = QFrame()
        left.setObjectName("findingsPanel")
        left_layout = QVBoxLayout(left)
        title = QLabel("漏洞列表")
        title.setObjectName("pageSectionTitle")
        left_layout.addWidget(title)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索名称、地址或网络区域")
        left_layout.addWidget(self.search_edit)

        create_row = QHBoxLayout()
        self.new_button = QPushButton("新建漏洞")
        self.library_button = QPushButton("从漏洞库添加")
        create_row.addWidget(self.new_button)
        create_row.addWidget(self.library_button)
        left_layout.addLayout(create_row)
        self.batch_button = QPushButton("批量录入")
        left_layout.addWidget(self.batch_button)

        self.list_view = QListView()
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.model = FindingsListModel(self.state, self)
        self.list_view.setModel(self.model)
        left_layout.addWidget(self.list_view, 1)

        action_row = QHBoxLayout()
        self.up_button = QPushButton("上移")
        self.down_button = QPushButton("下移")
        self.copy_button = QPushButton("复制")
        self.delete_button = QPushButton("删除")
        for button in (
            self.up_button,
            self.down_button,
            self.copy_button,
            self.delete_button,
        ):
            action_row.addWidget(button)
        left_layout.addLayout(action_row)

        right = QFrame()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.editor = FindingEditor(self.screenshots_dir)
        right_layout.addWidget(self.editor, 1)
        editor_actions = QHBoxLayout()
        editor_actions.addStretch(1)
        self.clear_button = QPushButton("清空表单")
        self.save_button = QPushButton("保存漏洞")
        self.save_button.setObjectName("primaryButton")
        editor_actions.addWidget(self.clear_button)
        editor_actions.addWidget(self.save_button)
        right_layout.addLayout(editor_actions)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([360, 980])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.search_edit.textChanged.connect(self.model.set_search_text)
        self.list_view.selectionModel().currentChanged.connect(
            self._on_view_selection_changed
        )
        self.new_button.clicked.connect(self.new_finding)
        self.library_button.clicked.connect(self.addFromLibraryRequested)
        self.addFromLibraryRequested.connect(self.open_library_picker)
        self.batch_button.clicked.connect(self.open_batch_dialog)
        self.clear_button.clicked.connect(self.new_finding)
        self.save_button.clicked.connect(self.save_current)
        self.up_button.clicked.connect(lambda: self._move_current(-1))
        self.down_button.clicked.connect(lambda: self._move_current(1))
        self.copy_button.clicked.connect(self._copy_current)
        self.delete_button.clicked.connect(self._delete_current)

    def set_state(self, state: ProjectState) -> None:
        self.state = state
        self.model.set_state(state)
        self.current_index = None
        self.editor.clear_form()
        self.list_view.clearSelection()

    def save_current(self) -> bool:
        try:
            data = self.editor.finding_data()
        except FindingValidationError as exc:
            QMessageBox.warning(self, "无法保存漏洞", str(exc))
            return False
        if self.current_index is None:
            self.state.findings.append(data)
            self.current_index = len(self.state.findings) - 1
        elif 0 <= self.current_index < len(self.state.findings):
            self.state.findings[self.current_index] = data
        else:
            return False
        self.editor.mark_clean()
        self._notify_mutation()
        self._select_current_in_view()
        return True

    def commit_active(self) -> bool:
        if self.editor.is_dirty():
            return self.save_current()
        return True

    def request_selection(self, index: int) -> bool:
        if not 0 <= index < len(self.state.findings):
            return False
        if index == self.current_index:
            return True
        if self.editor.is_dirty():
            decision = self.confirm_unsaved()
            if decision == "cancel":
                self._select_current_in_view()
                return False
            if decision == "save" and not self.save_current():
                self._select_current_in_view()
                return False
        self.current_index = index
        self.editor.set_finding(self.state.findings[index])
        self._select_current_in_view()
        return True

    def confirm_unsaved(self) -> str:
        box = QMessageBox(self)
        box.setWindowTitle("未保存的漏洞")
        box.setText("当前漏洞存在未保存内容。")
        save = box.addButton("保存", QMessageBox.AcceptRole)
        discard = box.addButton("放弃", QMessageBox.DestructiveRole)
        box.addButton("取消", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is save:
            return "save"
        if box.clickedButton() is discard:
            return "discard"
        return "cancel"

    def new_finding(self) -> bool:
        if self.editor.is_dirty():
            decision = self.confirm_unsaved()
            if decision == "cancel":
                return False
            if decision == "save" and not self.save_current():
                return False
        self.current_index = None
        self.editor.clear_form()
        self.list_view.clearSelection()
        self.editor.name_edit.setFocus()
        return True

    def append_finding(self, finding: dict, focus_address: bool = False) -> int:
        self.state.findings.append(copy.deepcopy(finding))
        self.current_index = len(self.state.findings) - 1
        self._notify_mutation()
        self.editor.set_finding(self.state.findings[self.current_index])
        self._select_current_in_view()
        if focus_address:
            self.editor.focus_address()
        return self.current_index

    def copy_finding(self, index: int) -> bool:
        if not 0 <= index < len(self.state.findings):
            return False
        duplicate = copy.deepcopy(self.state.findings[index])
        name = duplicate.get("name", "")
        if not name.endswith("(副本)"):
            duplicate["name"] = f"{name} (副本)".strip()
        self.state.findings.insert(index + 1, duplicate)
        self.current_index = index + 1
        self._notify_mutation()
        self.editor.set_finding(duplicate)
        self._select_current_in_view()
        return True

    def move_finding(self, index: int, direction: int) -> bool:
        target = index + direction
        if not (
            0 <= index < len(self.state.findings)
            and 0 <= target < len(self.state.findings)
        ):
            return False
        self.state.findings[index], self.state.findings[target] = (
            self.state.findings[target],
            self.state.findings[index],
        )
        if self.current_index == index:
            self.current_index = target
        elif self.current_index == target:
            self.current_index = index
        self._notify_mutation()
        self._select_current_in_view()
        return True

    def delete_finding(self, index: int, confirm: bool = True) -> bool:
        if not 0 <= index < len(self.state.findings):
            return False
        if confirm:
            answer = QMessageBox.question(
                self,
                "删除漏洞",
                f"确定删除“{self.state.findings[index].get('name', '')}”吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False
        self.state.findings.pop(index)
        self.current_index = None
        self.editor.clear_form()
        self._notify_mutation()
        return True

    def set_search_text(self, text: str) -> None:
        self.search_edit.setText(text)

    def visible_finding_names(self) -> list[str]:
        return [
            self.state.findings[index].get("name", "")
            for index in self.model._visible_indices
        ]

    def open_batch_dialog(self) -> None:
        if not self._resolve_unsaved_editor():
            return
        dialog = BatchAddDialog(self.vuln_manager, self)
        if dialog.exec() and dialog.created_findings:
            self.state.findings.extend(copy.deepcopy(dialog.created_findings))
            self.current_index = len(self.state.findings) - 1
            self._notify_mutation()
            self.editor.set_finding(self.state.findings[self.current_index])
            self._select_current_in_view()

    def open_library_picker(self) -> None:
        if not self._resolve_unsaved_editor():
            return
        picker = LibraryPicker(self.vuln_manager, self)
        if not picker.exec():
            return
        template = picker.selected_template()
        if template:
            finding = create_finding(self.vuln_manager, vuln_id=template["id"])
            self.append_finding(finding, focus_address=True)

    def _notify_mutation(self) -> None:
        self.state.mark_dirty()
        self.model.refresh()
        self.stateChanged.emit()

    def _on_view_selection_changed(self, current, _previous) -> None:
        if self._syncing_selection or not current.isValid():
            return
        index = self.model.finding_index(current.row())
        if index is not None:
            self.request_selection(index)

    def _select_current_in_view(self) -> None:
        self._syncing_selection = True
        try:
            if self.current_index is None:
                self.list_view.clearSelection()
                return
            row = self.model.row_for_finding(self.current_index)
            if row is not None:
                self.list_view.setCurrentIndex(self.model.index(row, 0))
        finally:
            self._syncing_selection = False

    def _move_current(self, direction: int) -> None:
        if self.current_index is not None:
            self.move_finding(self.current_index, direction)

    def _copy_current(self) -> None:
        if self.current_index is not None and self._resolve_unsaved_editor():
            self.copy_finding(self.current_index)

    def _resolve_unsaved_editor(self) -> bool:
        if not self.editor.is_dirty():
            return True
        decision = self.confirm_unsaved()
        if decision == "cancel":
            return False
        if decision == "save":
            return self.save_current()
        if self.current_index is None:
            self.editor.clear_form()
        elif 0 <= self.current_index < len(self.state.findings):
            self.editor.set_finding(self.state.findings[self.current_index])
        return True

    def _delete_current(self) -> None:
        if self.current_index is not None:
            self.delete_finding(self.current_index)
