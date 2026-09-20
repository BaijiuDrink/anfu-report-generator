import pytest

from app_state import ProjectState
from ui.dialogs.batch_add_dialog import BatchAddDialog
from ui.pages.findings_page import FindingsPage


def make_state():
    return ProjectState(
        findings=[
            {
                "name": "one",
                "url": "a",
                "network_zone": "互联网",
                "risk_level": "中危",
            },
            {
                "name": "two",
                "url": "b",
                "network_zone": "内网",
                "risk_level": "高危",
            },
        ]
    )


def test_copy_move_and_search(qtbot, tmp_path, vuln_manager):
    page = FindingsPage(tmp_path, vuln_manager)
    qtbot.addWidget(page)
    state = make_state()
    page.set_state(state)
    page.copy_finding(0)
    assert state.findings[1]["name"] == "one (副本)"
    page.move_finding(1, 1)
    assert state.findings[2]["name"] == "one (副本)"
    page.set_search_text("two")
    assert page.visible_finding_names() == ["two"]


def test_cancel_keeps_current_selection_and_edits(
    qtbot, tmp_path, vuln_manager, monkeypatch
):
    page = FindingsPage(tmp_path, vuln_manager)
    qtbot.addWidget(page)
    page.set_state(make_state())
    page.request_selection(0)
    page.editor.name_edit.setText("edited")
    monkeypatch.setattr(page, "confirm_unsaved", lambda: "cancel")
    assert page.request_selection(1) is False
    assert page.current_index == 0
    assert page.editor.name_edit.text() == "edited"


def test_batch_dialog_validates_required_fields(qtbot, vuln_manager):
    dialog = BatchAddDialog(vuln_manager)
    qtbot.addWidget(dialog)
    with pytest.raises(ValueError, match="漏洞ID不能为空"):
        dialog.build_findings()

    dialog.vuln_id_edit.setText("sql-injection")
    with pytest.raises(ValueError, match="至少输入一个"):
        dialog.build_findings()


def test_batch_dialog_rejects_unknown_id(qtbot, vuln_manager):
    dialog = BatchAddDialog(vuln_manager)
    qtbot.addWidget(dialog)
    dialog.vuln_id_edit.setText("unknown")
    dialog.hosts_edit.setPlainText("10.0.0.1")
    with pytest.raises(ValueError, match="未找到ID"):
        dialog.build_findings()


def test_batch_dialog_ignores_blank_lines(qtbot, vuln_manager):
    dialog = BatchAddDialog(vuln_manager)
    qtbot.addWidget(dialog)
    dialog.vuln_id_edit.setText("sql-injection")
    dialog.hosts_edit.setPlainText("10.0.0.1\n\n  \n10.0.0.2")
    dialog.custom_name_edit.setText("批量漏洞")

    findings = dialog.build_findings()

    assert [item["url"] for item in findings] == ["10.0.0.1", "10.0.0.2"]
    assert all(item["name"] == "批量漏洞" for item in findings)
