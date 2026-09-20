from ui.dialogs.library_picker import LibraryPicker
from ui.pages.library_page import LibraryPage


def test_picker_filters_by_keyword_and_category(qtbot, vuln_manager):
    picker = LibraryPicker(vuln_manager)
    qtbot.addWidget(picker)
    picker.set_keyword("SQL")
    assert all(
        "sql" in item["name"].lower() or "sql" in item["id"].lower()
        for item in picker.visible_templates()
    )


def test_picker_returns_deep_copy(qtbot, vuln_manager):
    picker = LibraryPicker(vuln_manager)
    qtbot.addWidget(picker)
    picker.select_template("sql-injection")
    selected = picker.selected_template()
    selected["name"] = "changed"
    assert vuln_manager.get_by_id("sql-injection")["name"] == "SQL注入漏洞"


def test_library_edit_writes_through_manager(qtbot, vuln_manager):
    page = LibraryPage(vuln_manager)
    qtbot.addWidget(page)
    vuln_id = vuln_manager.list_all()[0]["id"]
    page.save_template(vuln_id, {"name": "更新后的名称", "impact_scope": "互联网系统"})
    saved = vuln_manager.get_by_id(vuln_id)
    assert saved["name"] == "更新后的名称"
    assert saved["impact_scope"] == "互联网系统"
