import json

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMessageBox
import pytest

from app_state import ProjectState
from services.project_history import ProjectHistory
from services.project_store import ProjectStore
from services.report_service import ReportService
from ui.main_window import MainWindow


@pytest.fixture
def window_deps(tmp_path, vuln_manager):
    project_path = tmp_path / "next.json"
    project_path.write_text(
        json.dumps({"project_name": "next", "findings": []}), encoding="utf-8"
    )
    deps = {
        "state": ProjectState(),
        "project_store": ProjectStore(),
        "report_service": ReportService(),
        "vuln_manager": vuln_manager,
        "screenshots_dir": tmp_path / "screenshots",
        "project_history": ProjectHistory(tmp_path / "recent-projects.json"),
    }
    return deps, project_path


def test_cancel_prevents_project_replacement(qtbot, window_deps, monkeypatch):
    deps, project_path = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    window.state.replace("old", [{"name": "old"}], None)
    window.state.mark_dirty()
    monkeypatch.setattr(window, "confirm_project_change", lambda: "cancel")
    assert window.open_project(project_path) is False
    assert window.state.project_name == "old"
    window.state.mark_clean()


def test_failed_open_preserves_current_state(qtbot, window_deps, monkeypatch):
    deps, project_path = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    window.state.replace("old", [{"name": "old"}], None)
    monkeypatch.setattr(
        deps["project_store"],
        "load",
        lambda path: (_ for _ in ()).throw(ValueError("broken")),
    )
    monkeypatch.setattr("ui.main_window.QMessageBox.critical", lambda *args: None)
    assert window.open_project(project_path) is False
    assert window.state.project_name == "old"


def test_navigation_shows_findings_and_library_pages(qtbot, window_deps):
    deps, _ = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    window.show_library_page()
    assert window.page_stack.currentWidget() is window.library_page
    window.show_findings_page()
    assert window.page_stack.currentWidget() is window.findings_page


@pytest.mark.parametrize(
    ("decision", "expected_page", "expected_name"),
    [
        ("cancel", "findings", "one"),
        ("discard", "library", "one"),
        ("save", "library", "edited"),
    ],
)
def test_page_switch_honors_unsaved_decision(
    qtbot, window_deps, monkeypatch, decision, expected_page, expected_name
):
    deps, _ = window_deps
    deps["state"].findings = [{"name": "one"}]
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    window.findings_page.request_selection(0)
    window.findings_page.editor.name_edit.setText("edited")
    monkeypatch.setattr(window.findings_page, "confirm_unsaved", lambda: decision)

    window.show_library_page()

    expected_widget = (
        window.findings_page if expected_page == "findings" else window.library_page
    )
    assert window.page_stack.currentWidget() is expected_widget
    assert window.state.findings[0]["name"] == expected_name
    window.state.mark_clean()
    window.findings_page.editor.mark_clean()


def test_close_cancel_keeps_window_open(qtbot, window_deps, monkeypatch):
    deps, _ = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    window.state.mark_dirty()
    monkeypatch.setattr(window, "confirm_project_change", lambda: "cancel")
    event = QCloseEvent()

    window.closeEvent(event)

    assert event.isAccepted() is False
    window.state.mark_clean()


def test_failed_save_preserves_dirty_state(qtbot, window_deps, monkeypatch, tmp_path):
    deps, _ = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    window.state.findings = [{"name": "one"}]
    window.state.mark_dirty()
    monkeypatch.setattr(
        deps["project_store"],
        "save",
        lambda *args: (_ for _ in ()).throw(OSError("readonly")),
    )
    monkeypatch.setattr("ui.main_window.QMessageBox.critical", lambda *args: None)

    assert window.save_project(tmp_path / "project.json") is False
    assert window.state.dirty is True
    assert deps["project_history"].entries() == []
    window.state.mark_clean()


def test_save_state_chip_tracks_editor_changes(qtbot, window_deps):
    deps, _ = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)

    assert "已保存" in window.save_state_label.text()
    window.findings_page.editor.name_edit.setText("待处理漏洞")
    assert "未保存" in window.save_state_label.text()
    window.findings_page.editor.mark_clean()
    assert "已保存" in window.save_state_label.text()


def test_successful_open_and_save_enter_history(qtbot, window_deps):
    deps, project_path = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)

    assert window.open_project(project_path) is True
    assert len(deps["project_history"].entries()) == 1
    assert deps["project_history"].entries()[0].name == "next"

    window.state.findings.append({"name": "one"})
    assert window.save_project(project_path) is True
    assert len(deps["project_history"].entries()) == 1
    assert deps["project_history"].entries()[0].path == project_path.resolve()


def test_projects_navigation_shows_history_page(qtbot, window_deps):
    deps, _ = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)

    assert window.show_projects_page() is True
    assert window.page_stack.currentWidget() is window.projects_page
    assert window.projects_nav.isChecked()


def test_recent_open_rechecks_missing_path(qtbot, window_deps):
    deps, project_path = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    entry = deps["project_history"].record(project_path, "next")
    window.show_projects_page()
    renamed = project_path.with_name("renamed.json")
    project_path.rename(renamed)

    assert window.open_recent_project(entry.record_id) is True
    assert window.state.project_path == renamed.resolve()
    assert window.page_stack.currentWidget() is window.findings_page


def test_recent_open_cancel_preserves_current_project(
    qtbot, window_deps, monkeypatch, tmp_path
):
    deps, project_path = window_deps
    deps["state"].replace("old", [{"name": "old"}], tmp_path / "old.json")
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    entry = deps["project_history"].record(project_path, "next")
    window.show_projects_page()
    window.state.mark_dirty()
    monkeypatch.setattr(window, "confirm_project_change", lambda: "cancel")

    assert window.open_recent_project(entry.record_id) is False
    assert window.state.project_name == "old"
    assert window.state.project_path == tmp_path / "old.json"
    assert window.page_stack.currentWidget() is window.projects_page
    window.state.mark_clean()


def test_failed_open_is_not_added_to_history(qtbot, window_deps, monkeypatch, tmp_path):
    deps, _ = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr("ui.main_window.QMessageBox.critical", lambda *args: None)

    assert window.open_project(invalid) is False
    assert deps["project_history"].entries() == []


def test_projects_navigation_cancel_keeps_editor(qtbot, window_deps, monkeypatch):
    deps, _ = window_deps
    deps["state"].findings = [{"name": "原漏洞"}]
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    window.findings_page.request_selection(0)
    window.findings_page.editor.name_edit.setText("未保存修改")
    monkeypatch.setattr(window.findings_page, "confirm_unsaved", lambda: "cancel")

    assert window.show_projects_page() is False
    assert window.page_stack.currentWidget() is window.findings_page
    assert window.findings_page.editor.name_edit.text() == "未保存修改"
    window.findings_page.editor.mark_clean()


def test_manual_relocate_updates_record(qtbot, window_deps, tmp_path):
    deps, project_path = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    entry = deps["project_history"].record(project_path, "next")
    moved_dir = tmp_path / "moved"
    moved_dir.mkdir()
    moved = moved_dir / "next.json"
    project_path.rename(moved)

    assert window.relocate_recent_project(entry.record_id, moved) is True
    updated = deps["project_history"].get(entry.record_id)
    assert updated.path == moved.resolve()
    assert updated.original_dir == moved_dir.resolve()
    assert window.state.project_path is None


def test_name_mismatch_needs_confirmation(qtbot, window_deps, monkeypatch, tmp_path):
    deps, project_path = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    entry = deps["project_history"].record(project_path, "next")
    different = tmp_path / "different.json"
    different.write_text(
        json.dumps({"project_name": "different", "findings": []}), encoding="utf-8"
    )
    monkeypatch.setattr(
        "ui.main_window.QMessageBox.question", lambda *args: QMessageBox.No
    )

    assert window.relocate_recent_project(entry.record_id, different) is False
    assert deps["project_history"].get(entry.record_id).path == project_path.resolve()


def test_invalid_relocate_keeps_record_and_active_project(
    qtbot, window_deps, monkeypatch, tmp_path
):
    deps, project_path = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    entry = deps["project_history"].record(project_path, "next")
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr("ui.main_window.QMessageBox.critical", lambda *args: None)

    assert window.relocate_recent_project(entry.record_id, invalid) is False
    assert deps["project_history"].get(entry.record_id).path == project_path.resolve()
    assert window.state.project_path is None


def test_remove_history_keeps_json_file(qtbot, window_deps):
    deps, project_path = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    entry = deps["project_history"].record(project_path, "next")

    window.remove_recent_project(entry.record_id)

    assert deps["project_history"].get(entry.record_id) is None
    assert project_path.is_file()


def test_history_write_error_does_not_fail_project_save(
    qtbot, window_deps, monkeypatch, tmp_path
):
    deps, _ = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    window.state.findings = [{"name": "one"}]

    def unavailable(*_args):
        raise OSError("history is readonly")

    monkeypatch.setattr(deps["project_history"], "record", unavailable)
    destination = tmp_path / "saved.json"

    assert window.save_project(destination) is True
    assert destination.is_file()
    assert "历史记录更新失败" in window.statusBar().currentMessage()
