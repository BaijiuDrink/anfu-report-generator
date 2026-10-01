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


def test_poc_exp_text_round_trips_without_losing_indentation(qtbot, tmp_path):
    editor = FindingEditor(tmp_path)
    qtbot.addWidget(editor)
    code = "if authorized:\n    run_exp()\n        print('done')"
    editor.set_finding({"name": "命令执行", "poc_exp": code})

    assert editor.poc_exp_edit.toPlainText() == code
    assert editor.finding_data()["poc_exp"] == code


def test_editing_poc_exp_marks_finding_dirty(qtbot, tmp_path):
    editor = FindingEditor(tmp_path)
    qtbot.addWidget(editor)
    editor.set_finding({"name": "命令执行"})
    editor.mark_clean()

    editor.poc_exp_edit.setPlainText("id")

    assert editor.is_dirty() is True


def test_choice_pills_are_exclusive_and_saved(qtbot, tmp_path):
    editor = FindingEditor(tmp_path)
    qtbot.addWidget(editor)
    editor.set_finding({"name": "测试漏洞"})

    for group, value in (
        (editor.risk_group, "高危"),
        (editor.zone_group, "内网"),
        (editor.priority_group, "紧急"),
    ):
        next(
            button for button in group.buttons() if button.property("value") == value
        ).click()
        assert [
            button.property("value") for button in group.buttons() if button.isChecked()
        ] == [value]

    result = editor.finding_data()
    assert result["risk_level"] == "高危"
    assert result["network_zone"] == "内网"
    assert result["fix_priority"] == "紧急"
    assert editor.is_dirty() is True
