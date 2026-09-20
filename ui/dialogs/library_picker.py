from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


def template_preview(template: dict | None) -> str:
    if not template:
        return "请选择一个漏洞模板查看详情。"
    labels = (
        ("ID", "id"),
        ("名称", "name"),
        ("分类", "category"),
        ("风险等级", "risk_level"),
        ("修复优先级", "fix_priority"),
        ("漏洞描述", "description"),
        ("验证步骤", "verify_steps"),
        ("验证结果", "verify_result"),
        ("影响范围", "impact_scope"),
        ("修复建议", "fix_suggestion"),
        ("整改验证方法", "fix_verify"),
    )
    return "\n\n".join(
        f"{label}\n{template.get(key, '') or '未填写'}" for label, key in labels
    )


class LibraryPicker(QDialog):
    def __init__(self, vuln_manager, parent=None):
        super().__init__(parent)
        self.vuln_manager = vuln_manager
        self._visible_templates: list[dict] = []
        self.setWindowTitle("从漏洞库添加")
        self.resize(980, 680)

        root = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("搜索漏洞名称或 ID")
        self.category_combo = QComboBox()
        self.category_combo.addItem("全部分类")
        self.category_combo.addItems(self.vuln_manager.get_categories())
        filters.addWidget(self.keyword_edit, 1)
        filters.addWidget(self.category_combo)
        root.addLayout(filters)

        splitter = QSplitter(Qt.Horizontal)
        self.list_widget = QListWidget()
        self.preview = QTextBrowser()
        self.preview.setPlainText(template_preview(None))
        splitter.addWidget(self.list_widget)
        splitter.addWidget(self.preview)
        splitter.setSizes([340, 620])
        root.addWidget(splitter, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("取消")
        self.add_button = QPushButton("添加到项目")
        self.add_button.setObjectName("primaryButton")
        self.add_button.setEnabled(False)
        actions.addWidget(cancel)
        actions.addWidget(self.add_button)
        root.addLayout(actions)

        self.keyword_edit.textChanged.connect(self.refresh)
        self.category_combo.currentTextChanged.connect(self.refresh)
        self.list_widget.currentItemChanged.connect(self._update_preview)
        self.list_widget.itemDoubleClicked.connect(lambda _item: self.accept())
        cancel.clicked.connect(self.reject)
        self.add_button.clicked.connect(self.accept)
        self.refresh()

    def refresh(self) -> None:
        keyword = self.keyword_edit.text().casefold().strip()
        category = self.category_combo.currentText()
        self._visible_templates = []
        for template in self.vuln_manager.list_all():
            searchable = (
                f"{template.get('id', '')} {template.get('name', '')}".casefold()
            )
            if keyword and keyword not in searchable:
                continue
            if category != "全部分类" and template.get("category", "其他") != category:
                continue
            self._visible_templates.append(template)
        self.list_widget.clear()
        for template in self._visible_templates:
            item = QListWidgetItem(
                f"{template.get('name', '未命名')}\n{template.get('id', '')} · {template.get('risk_level', '中危')}"
            )
            item.setData(Qt.UserRole, template.get("id"))
            self.list_widget.addItem(item)
        self.add_button.setEnabled(False)
        self.preview.setPlainText(template_preview(None))

    def set_keyword(self, keyword: str) -> None:
        self.keyword_edit.setText(keyword)

    def visible_templates(self) -> list[dict]:
        return list(self._visible_templates)

    def select_template(self, vuln_id: str) -> bool:
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item.data(Qt.UserRole) == vuln_id:
                self.list_widget.setCurrentRow(row)
                return True
        return False

    def selected_template(self) -> dict | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return self.vuln_manager.get_by_id(item.data(Qt.UserRole))

    def _update_preview(self, current, _previous) -> None:
        template = (
            self.vuln_manager.get_by_id(current.data(Qt.UserRole)) if current else None
        )
        self.preview.setPlainText(template_preview(template))
        self.add_button.setEnabled(template is not None)
