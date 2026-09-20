import pytest

from ui.widgets.finding_editor import FindingEditor, FindingValidationError


def test_defaults_and_round_trip(qtbot, tmp_path):
    editor = FindingEditor(tmp_path)
    qtbot.addWidget(editor)
    editor.set_finding({"vuln_id": "oauth", "name": "凭证泄露", "url": "a\nb"})
    result = editor.finding_data()
    assert result["vuln_id"] == "oauth"
    assert result["name"] == "凭证泄露"
    assert result["url"] == "a\nb"
    assert result["network_zone"] == "互联网"
    assert result["risk_level"] == "中危"
    assert result["fix_priority"] == "高"


def test_name_is_required(qtbot, tmp_path):
    editor = FindingEditor(tmp_path)
    qtbot.addWidget(editor)
    with pytest.raises(FindingValidationError, match="漏洞名称不能为空"):
        editor.finding_data()


def test_user_edit_marks_dirty_and_mark_clean_resets(qtbot, tmp_path):
    editor = FindingEditor(tmp_path)
    qtbot.addWidget(editor)
    editor.set_finding({"name": "原名称"})
    assert editor.is_dirty() is False

    editor.name_edit.setText("新名称")
    assert editor.is_dirty() is True

    editor.mark_clean()
    assert editor.is_dirty() is False


def test_clear_form_restores_defaults_without_transient_dirty_event(qtbot, tmp_path):
    editor = FindingEditor(tmp_path)
    qtbot.addWidget(editor)
    editor.set_finding({"name": "x", "risk_level": "高危"})
    events = []
    editor.dirtyChanged.connect(events.append)

    editor.clear_form()

    assert editor.is_dirty() is False
    assert editor.risk_group.checkedButton().property("value") == "中危"
    assert True not in events
