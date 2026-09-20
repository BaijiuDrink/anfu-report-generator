from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from vuln_manager import FIX_PRIORITIES, RISK_LEVELS


class VulnEditDialog(QDialog):
    def __init__(self, existing: dict | None = None, parent=None):
        super().__init__(parent)
        self.existing = existing or {}
        self.setWindowTitle("编辑漏洞模板" if existing else "新建漏洞模板")
        self.resize(720, 760)

        root = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        form = QFormLayout(container)
        self.id_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.category_edit = QLineEdit()
        self.risk_combo = QComboBox()
        self.risk_combo.addItems(RISK_LEVELS)
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(FIX_PRIORITIES)
        form.addRow("漏洞 ID", self.id_edit)
        form.addRow("漏洞名称", self.name_edit)
        form.addRow("分类", self.category_edit)
        form.addRow("风险等级", self.risk_combo)
        form.addRow("修复优先级", self.priority_combo)

        self.text_edits = {}
        for key, label in (
            ("description", "漏洞描述"),
            ("verify_steps", "验证步骤"),
            ("verify_result", "验证结果"),
            ("impact_scope", "影响范围"),
            ("fix_suggestion", "修复建议"),
            ("fix_verify", "整改验证方法"),
        ):
            editor = QPlainTextEdit()
            editor.setMinimumHeight(95)
            editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.text_edits[key] = editor
            form.addRow(label, editor)
        scroll.setWidget(container)
        root.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._load_existing()

    def _load_existing(self) -> None:
        self.id_edit.setText(self.existing.get("id", ""))
        self.id_edit.setEnabled(not bool(self.existing))
        self.name_edit.setText(self.existing.get("name", ""))
        self.category_edit.setText(self.existing.get("category", "其他"))
        self.risk_combo.setCurrentText(self.existing.get("risk_level", "中危"))
        self.priority_combo.setCurrentText(self.existing.get("fix_priority", "高"))
        for key, editor in self.text_edits.items():
            editor.setPlainText(self.existing.get(key, "") or "")

    def result_data(self) -> dict | None:
        vuln_id = self.id_edit.text().strip()
        name = self.name_edit.text().strip()
        if not vuln_id:
            raise ValueError("漏洞ID不能为空")
        if not name:
            raise ValueError("漏洞名称不能为空")
        result = {
            "id": vuln_id,
            "name": name,
            "category": self.category_edit.text().strip() or "其他",
            "risk_level": self.risk_combo.currentText(),
            "fix_priority": self.priority_combo.currentText(),
        }
        result.update(
            {
                key: editor.toPlainText().strip()
                for key, editor in self.text_edits.items()
            }
        )
        return result

    def accept(self) -> None:
        try:
            self.result_data()
        except ValueError as exc:
            QMessageBox.warning(self, "无法保存模板", str(exc))
            return
        super().accept()
