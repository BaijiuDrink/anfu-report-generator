import json

from PySide6.QtGui import QCloseEvent
import pytest

from app_state import ProjectState
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
    window.state.mark_clean()
