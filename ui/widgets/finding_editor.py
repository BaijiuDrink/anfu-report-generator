from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.evidence_editor import EvidenceEditor

FIELD_DEFAULTS = {
    "network_zone": "互联网",
    "risk_level": "中危",
    "fix_priority": "高",
}

STANDARD_FIELDS = {
    "vuln_id",
    "name",
    "url",
    "network_zone",
    "risk_level",
    "description",
    "verify_steps",
    "verify_result",
    "fix_suggestion",
    "fix_priority",
    "fix_verify",
}


class FindingValidationError(ValueError):
    pass


class FindingEditor(QWidget):
    dirtyChanged = Signal(bool)

    def __init__(self, screenshot_dir: Path, parent=None):
        super().__init__(parent)
        self.screenshot_dir = Path(screenshot_dir)
        self.vuln_id = None
        self._extra_fields = {}
        self._dirty = False
        self._loading = False
        self._build_ui()
        self._connect_dirty_signals()
        self.clear_form()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        form_widget = QWidget()
        self.form_layout = QVBoxLayout(form_widget)
        self.form_layout.setContentsMargins(16, 16, 16, 16)
        self.form_layout.setSpacing(14)
        scroll.setWidget(form_widget)
        root.addWidget(scroll)

        basic = QGroupBox("基本信息")
        basic_form = QFormLayout(basic)
        basic_form.setLabelAlignment(Qt.AlignTop)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入漏洞名称")
        self.url_edit = self._plain_text(88, "每行一个漏洞地址或受影响主机")
        zone_widget, self.zone_group = self._radio_field(["互联网", "内网"])
        risk_widget, self.risk_group = self._radio_field(
            ["严重", "高危", "中危", "低危", "信息"]
        )
        priority_widget, self.priority_group = self._radio_field(
            ["紧急", "高", "中", "低"]
        )
        basic_form.addRow("漏洞名称", self.name_edit)
        basic_form.addRow("漏洞地址", self.url_edit)
        basic_form.addRow("网络区域", zone_widget)
        basic_form.addRow("风险等级", risk_widget)
        basic_form.addRow("修复优先级", priority_widget)
        self.form_layout.addWidget(basic)

        content = QGroupBox("漏洞内容")
        content_form = QFormLayout(content)
        content_form.setLabelAlignment(Qt.AlignTop)
        self.description_edit = self._plain_text(130, "说明漏洞成因、触发条件和影响")
        content_form.addRow("漏洞描述", self.description_edit)
        self.form_layout.addWidget(content)

        verification = QGroupBox("验证证据")
        verification_form = QFormLayout(verification)
        verification_form.setLabelAlignment(Qt.AlignTop)
        self.evidence_edit = EvidenceEditor(self.screenshot_dir)
        self.evidence_edit.setMinimumHeight(220)
        self.evidence_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.verify_result_edit = self._plain_text(100, "填写验证结论")
        verification_form.addRow("漏洞验证", self.evidence_edit)
        verification_form.addRow("验证结果", self.verify_result_edit)
        self.form_layout.addWidget(verification)

        remediation = QGroupBox("整改建议")
        remediation_form = QFormLayout(remediation)
        remediation_form.setLabelAlignment(Qt.AlignTop)
        self.fix_suggestion_edit = self._plain_text(130, "填写可落地的修复措施")
        self.fix_verify_edit = self._plain_text(110, "填写整改后的验证方法")
        remediation_form.addRow("修复建议", self.fix_suggestion_edit)
        remediation_form.addRow("整改验证方法", self.fix_verify_edit)
        self.form_layout.addWidget(remediation)
        self.form_layout.addStretch(1)

    @staticmethod
    def _plain_text(minimum_height: int, placeholder: str) -> QPlainTextEdit:
        editor = QPlainTextEdit()
        editor.setMinimumHeight(minimum_height)
        editor.setPlaceholderText(placeholder)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        return editor

    @staticmethod
    def _radio_field(values: list[str]) -> tuple[QWidget, QButtonGroup]:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        group = QButtonGroup(widget)
        for value in values:
            button = QRadioButton(value)
            button.setProperty("value", value)
            group.addButton(button)
            layout.addWidget(button)
        layout.addStretch(1)
        return widget, group

    def _connect_dirty_signals(self) -> None:
        self.name_edit.textChanged.connect(self._mark_from_user)
        for editor in (
            self.url_edit,
            self.description_edit,
            self.evidence_edit,
            self.verify_result_edit,
            self.fix_suggestion_edit,
            self.fix_verify_edit,
        ):
            editor.textChanged.connect(self._mark_from_user)
        for group in (self.zone_group, self.risk_group, self.priority_group):
            group.buttonToggled.connect(self._on_button_toggled)

    def _mark_from_user(self, *_args) -> None:
        if not self._loading:
            self._set_dirty(True)

    def _on_button_toggled(self, _button, checked: bool) -> None:
        if checked:
            self._mark_from_user()

    def _set_dirty(self, value: bool) -> None:
        if self._dirty == value:
            return
        self._dirty = value
        self.dirtyChanged.emit(value)

    @staticmethod
    def _set_checked(group: QButtonGroup, value: str) -> None:
        for button in group.buttons():
            if button.property("value") == value:
                button.setChecked(True)
                return
        if group.buttons():
            group.buttons()[0].setChecked(True)

    def set_finding(self, finding: dict | None) -> None:
        data = copy.deepcopy(finding or {})
        self._loading = True
        try:
            self.vuln_id = data.get("vuln_id")
            self._extra_fields = {
                key: value for key, value in data.items() if key not in STANDARD_FIELDS
            }
            self.name_edit.setText(data.get("name", "") or "")
            self.url_edit.setPlainText(data.get("url", "") or "")
            self._set_checked(
                self.zone_group,
                data.get("network_zone") or FIELD_DEFAULTS["network_zone"],
            )
            self._set_checked(
                self.risk_group,
                data.get("risk_level") or FIELD_DEFAULTS["risk_level"],
            )
            self._set_checked(
                self.priority_group,
                data.get("fix_priority") or FIELD_DEFAULTS["fix_priority"],
            )
            self.description_edit.setPlainText(data.get("description", "") or "")
            self.evidence_edit.set_marker_text(data.get("verify_steps", "") or "")
            self.verify_result_edit.setPlainText(data.get("verify_result", "") or "")
            self.fix_suggestion_edit.setPlainText(data.get("fix_suggestion", "") or "")
            self.fix_verify_edit.setPlainText(data.get("fix_verify", "") or "")
        finally:
            self._loading = False
        self._set_dirty(False)

    def finding_data(self) -> dict:
        name = self.name_edit.text().strip()
        if not name:
            raise FindingValidationError("漏洞名称不能为空")
        result = copy.deepcopy(self._extra_fields)
        result.update(
            {
                "name": name,
                "url": self.url_edit.toPlainText().strip(),
                "network_zone": self.zone_group.checkedButton().property("value"),
                "risk_level": self.risk_group.checkedButton().property("value"),
                "description": self.description_edit.toPlainText().strip(),
                "verify_steps": self.evidence_edit.marker_text(),
                "verify_result": self.verify_result_edit.toPlainText().strip(),
                "fix_suggestion": self.fix_suggestion_edit.toPlainText().strip(),
                "fix_priority": self.priority_group.checkedButton().property("value"),
                "fix_verify": self.fix_verify_edit.toPlainText().strip(),
                "vuln_id": self.vuln_id,
            }
        )
        return result

    def clear_form(self) -> None:
        self.set_finding(None)

    def is_dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._set_dirty(False)

    def focus_address(self) -> None:
        self.url_edit.setFocus()
