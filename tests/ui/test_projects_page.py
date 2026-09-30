from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy

from services.project_history import RecentProject


def make_project(tmp_path, record_id="one", name="示例项目", missing=False):
    path = tmp_path / f"{record_id}.json"
    if not missing:
        path.write_text('{"project_name":"示例项目","findings":[]}', encoding="utf-8")
    return RecentProject(
        record_id=record_id,
        name=name,
        path=path,
        original_dir=tmp_path,
        digest="abc",
        last_opened="2026-10-01T09:00:00+00:00",
    )


def test_project_cards_show_status(qtbot, tmp_path):
    from ui.pages.projects_page import ProjectsPage

    page = ProjectsPage()
    qtbot.addWidget(page)
    page.set_projects(
        [make_project(tmp_path), make_project(tmp_path, "two", "已搬迁", True)]
    )

    assert page.list_widget.count() == 2
    assert "示例项目" in page.list_widget.item(0).text()
    assert str(tmp_path / "one.json") in page.list_widget.item(0).text()
    assert "2026-10-01" in page.list_widget.item(0).text()
    assert "已搬迁 · JSON 文件已移动" in page.list_widget.item(1).text()


def test_search_filters_by_name_or_path(qtbot, tmp_path):
    from ui.pages.projects_page import ProjectsPage

    page = ProjectsPage()
    qtbot.addWidget(page)
    page.set_projects(
        [make_project(tmp_path), make_project(tmp_path, "two", "第二项目")]
    )

    page.search_edit.setText("第二")
    assert page.list_widget.count() == 1
    assert page.list_widget.item(0).data(Qt.UserRole) == "two"

    page.search_edit.setText("one.json")
    assert page.list_widget.count() == 1
    assert page.list_widget.item(0).data(Qt.UserRole) == "one"


def test_actions_emit_selected_record_id(qtbot, tmp_path):
    from ui.pages.projects_page import ProjectsPage

    page = ProjectsPage()
    qtbot.addWidget(page)
    page.set_projects([make_project(tmp_path)])
    opened = QSignalSpy(page.openRequested)
    relocated = QSignalSpy(page.relocateRequested)
    removed = QSignalSpy(page.removeRequested)

    page.open_button.click()
    page.relocate_button.click()
    page.remove_button.click()

    assert opened.at(0)[0] == "one"
    assert relocated.at(0)[0] == "one"
    assert removed.at(0)[0] == "one"


def test_empty_history_state(qtbot):
    from ui.pages.projects_page import ProjectsPage

    page = ProjectsPage()
    qtbot.addWidget(page)
    page.set_projects([])

    assert page.empty_label.isVisibleTo(page)
    assert not page.open_button.isEnabled()


def test_recent_open_time_is_displayed_in_local_timezone(qtbot, tmp_path):
    from ui.pages.projects_page import ProjectsPage

    project = make_project(tmp_path)
    expected = (
        datetime.fromisoformat(project.last_opened)
        .astimezone()
        .strftime("%Y-%m-%d %H:%M")
    )
    page = ProjectsPage()
    qtbot.addWidget(page)
    page.set_projects([project])

    assert f"最近打开 {expected}" in page.list_widget.item(0).text()
