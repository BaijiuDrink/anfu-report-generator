from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
)

from vuln_manager import NETWORK_ZONES, batch_create_findings


class BatchAddDialog(QDialog):
    def __init__(self, vuln_manager, parent=None):
        super().__init__(parent)
        self.vuln_manager = vuln_manager
        self.created_findings = []
        self.setWindowTitle("批量录入漏洞")
        self.resize(520, 420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.vuln_id_edit = QLineEdit()
        self.vuln_id_edit.setPlaceholderText("例如：sql-injection")
        self.zone_combo = QComboBox()
        self.zone_combo.addItems(NETWORK_ZONES)
        self.hosts_edit = QPlainTextEdit()
        self.hosts_edit.setPlaceholderText("每行一个 IP 地址或 URL")
        self.custom_name_edit = QLineEdit()
        self.custom_name_edit.setPlaceholderText("留空时使用漏洞库名称")
        form.addRow("漏洞 ID", self.vuln_id_edit)
        form.addRow("网络区域", self.zone_combo)
        form.addRow("主机列表", self.hosts_edit)
        form.addRow("自定义名称", self.custom_name_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("批量添加")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def build_findings(self) -> list[dict]:
        vuln_id = self.vuln_id_edit.text().strip()
        if not vuln_id:
            raise ValueError("漏洞ID不能为空")
        hosts = [line.strip() for line in self.hosts_edit.toPlainText().splitlines()]
        if not any(hosts):
            raise ValueError("请至少输入一个主机地址")
        return batch_create_findings(
            self.vuln_manager,
            vuln_id=vuln_id,
            hosts=hosts,
            network_zone=self.zone_combo.currentText(),
            custom_name=self.custom_name_edit.text().strip() or None,
        )

    def accept(self) -> None:
        try:
            self.created_findings = self.build_findings()
        except ValueError as exc:
            QMessageBox.warning(self, "无法批量添加", str(exc))
            return
        super().accept()
