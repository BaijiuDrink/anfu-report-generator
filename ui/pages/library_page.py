from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ui.dialogs.library_picker import template_preview
from ui.dialogs.vuln_edit_dialog import VulnEditDialog


class LibraryPage(QWidget):
    def __init__(self, vuln_manager, parent=None):
        super().__init__(parent)
        self.vuln_manager = vuln_manager
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("漏洞库")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.add_button = QPushButton("新建模板")
        self.edit_button = QPushButton("编辑")
        self.delete_button = QPushButton("删除")
        header.addWidget(self.add_button)
        header.addWidget(self.edit_button)
        header.addWidget(self.delete_button)
        root.addLayout(header)

        filters = QHBoxLayout()
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("搜索漏洞名称、ID 或分类")
        self.category_combo = QComboBox()
        filters.addWidget(self.keyword_edit, 1)
        filters.addWidget(self.category_combo)
        root.addLayout(filters)

        splitter = QSplitter(Qt.Horizontal)
        self.list_widget = QListWidget()
        self.preview = QTextBrowser()
        splitter.addWidget(self.list_widget)
        splitter.addWidget(self.preview)
        splitter.setSizes([380, 760])
        root.addWidget(splitter, 1)

        self.keyword_edit.textChanged.connect(self.refresh)
        self.category_combo.currentTextChanged.connect(self.refresh)
        self.list_widget.currentItemChanged.connect(self._update_preview)
        self.add_button.clicked.connect(self.add_template)
        self.edit_button.clicked.connect(self.edit_selected)
        self.delete_button.clicked.connect(self.delete_selected)

    def refresh(self) -> None:
        selected = self.selected_id()
        current_category = self.category_combo.currentText()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("全部分类")
        self.category_combo.addItems(self.vuln_manager.get_categories())
        if current_category:
            self.category_combo.setCurrentText(current_category)
        self.category_combo.blockSignals(False)

        keyword = self.keyword_edit.text().casefold().strip()
        category = self.category_combo.currentText()
        self.list_widget.clear()
        selected_row = None
        for template in self.vuln_manager.list_all():
            searchable = " ".join(
                str(template.get(key, "")) for key in ("id", "name", "category")
            ).casefold()
            if keyword and keyword not in searchable:
                continue
            if category != "全部分类" and template.get("category", "其他") != category:
                continue
            item = QListWidgetItem(
                f"{template.get('name', '未命名')}\n{template.get('id', '')} · {template.get('category', '其他')}"
            )
            item.setData(Qt.UserRole, template.get("id"))
            self.list_widget.addItem(item)
            if template.get("id") == selected:
                selected_row = self.list_widget.count() - 1
        if selected_row is not None:
            self.list_widget.setCurrentRow(selected_row)
        elif self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self.preview.setPlainText(template_preview(None))

    def selected_id(self) -> str | None:
        item = self.list_widget.currentItem()
        return item.data(Qt.UserRole) if item else None

    def save_template(self, vuln_id: str, updates: dict) -> dict:
        saved = self.vuln_manager.update(vuln_id, updates)
        self.refresh()
        return saved

    def add_template(self) -> None:
        dialog = VulnEditDialog(parent=self)
        while dialog.exec():
            try:
                self.vuln_manager.add(dialog.result_data())
            except ValueError as exc:
                QMessageBox.warning(dialog, "无法保存模板", str(exc))
                continue
            self.refresh()
            return

    def edit_selected(self) -> None:
        vuln_id = self.selected_id()
        existing = self.vuln_manager.get_by_id(vuln_id) if vuln_id else None
        if not existing:
            return
        dialog = VulnEditDialog(existing, self)
        while dialog.exec():
            try:
                self.save_template(vuln_id, dialog.result_data())
            except ValueError as exc:
                QMessageBox.warning(dialog, "无法保存模板", str(exc))
                continue
            return

    def delete_selected(self) -> None:
        vuln_id = self.selected_id()
        if not vuln_id:
            return
        answer = QMessageBox.question(
            self,
            "删除模板",
            "确定删除当前漏洞模板吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.vuln_manager.delete(vuln_id)
            self.refresh()

    def _update_preview(self, current, _previous) -> None:
        template = (
            self.vuln_manager.get_by_id(current.data(Qt.UserRole)) if current else None
        )
        self.preview.setPlainText(template_preview(template))
