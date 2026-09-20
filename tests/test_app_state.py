from pathlib import Path

from app_state import ProjectState


def test_replace_deep_copies_findings_and_marks_clean():
    source = [{"name": "SQL注入", "url": "https://example.test"}]
    state = ProjectState()

    state.replace("示例项目", source, Path("project.json"))
    source[0]["name"] = "changed"

    assert state.project_name == "示例项目"
    assert state.findings[0]["name"] == "SQL注入"
    assert state.project_path == Path("project.json")
    assert state.dirty is False


def test_clear_restores_empty_clean_state():
    state = ProjectState(project_name="x", findings=[{"name": "x"}], dirty=True)
    state.clear()
    assert state.project_name == ""
    assert state.findings == []
    assert state.project_path is None
    assert state.dirty is False
