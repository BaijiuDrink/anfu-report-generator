import json
from pathlib import Path

import pytest


def test_record_persists_and_updates(tmp_path):
    from services.project_history import ProjectHistory

    project = tmp_path / "project.json"
    project.write_text(
        json.dumps({"project_name": "第一次", "findings": []}), encoding="utf-8"
    )
    index = tmp_path / "recent-projects.json"
    history = ProjectHistory(index)

    first = history.record(project, "第一次")
    updated = history.record(project, "第二次")
    reloaded = ProjectHistory(index).entries()

    assert first.record_id == updated.record_id
    assert len(reloaded) == 1
    assert reloaded[0].name == "第二次"
    assert reloaded[0].path == project.resolve()


def test_refresh_recovers_same_directory_rename(tmp_path):
    from services.project_history import ProjectHistory

    original = tmp_path / "original.json"
    original.write_text('{"project_name":"示例","findings":[]}', encoding="utf-8")
    history = ProjectHistory(tmp_path / "history.json")
    history.record(original, "示例")
    renamed = tmp_path / "renamed.json"
    original.rename(renamed)

    assert history.refresh()[0].path == renamed.resolve()
    assert (
        ProjectHistory(tmp_path / "history.json").entries()[0].path == renamed.resolve()
    )


def test_forget_keeps_json(tmp_path):
    from services.project_history import ProjectHistory

    project = tmp_path / "project.json"
    project.write_text('{"project_name":"示例","findings":[]}', encoding="utf-8")
    history = ProjectHistory(tmp_path / "history.json")
    entry = history.record(project, "示例")

    history.forget(entry.record_id)

    assert history.entries() == []
    assert project.is_file()


def test_ambiguous_digest_stays_missing(tmp_path):
    from services.project_history import ProjectHistory

    original = tmp_path / "original.json"
    original.write_text('{"project_name":"示例","findings":[]}', encoding="utf-8")
    history = ProjectHistory(tmp_path / "history.json")
    history.record(original, "示例")
    first = tmp_path / "first.json"
    original.rename(first)
    (tmp_path / "second.json").write_bytes(first.read_bytes())

    assert history.refresh()[0].missing is True


def test_refresh_never_scans_other_directory(tmp_path):
    from services.project_history import ProjectHistory

    original = tmp_path / "original.json"
    original.write_text('{"project_name":"示例","findings":[]}', encoding="utf-8")
    history = ProjectHistory(tmp_path / "history.json")
    history.record(original, "示例")
    other = tmp_path / "other"
    other.mkdir()
    original.rename(other / "original.json")

    assert history.refresh()[0].missing is True


def test_unreadable_sibling_does_not_abort_refresh(tmp_path, monkeypatch):
    from services.project_history import ProjectHistory

    original = tmp_path / "original.json"
    original.write_text('{"project_name":"示例","findings":[]}', encoding="utf-8")
    history = ProjectHistory(tmp_path / "history.json")
    history.record(original, "示例")
    original.rename(tmp_path / "renamed.json")
    unreadable = tmp_path / "unreadable.json"
    unreadable.write_text("broken", encoding="utf-8")
    real_read_bytes = Path.read_bytes

    def read_bytes(path):
        if path == unreadable:
            raise OSError("access denied")
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)

    assert history.refresh()[0].path == (tmp_path / "renamed.json").resolve()


@pytest.mark.parametrize("broken", [b"{broken", b"[]"])
def test_corrupt_index_is_backed_up(tmp_path, broken):
    from services.project_history import ProjectHistory

    index = tmp_path / "history.json"
    index.write_bytes(broken)

    assert ProjectHistory(index).entries() == []
    backups = list(tmp_path.glob("history.json.corrupt*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == broken


def test_relink_keeps_identity_and_changes_scan_directory(tmp_path):
    from services.project_history import ProjectHistory

    original = tmp_path / "original.json"
    original.write_text('{"project_name":"示例","findings":[]}', encoding="utf-8")
    history = ProjectHistory(tmp_path / "history.json")
    entry = history.record(original, "示例")
    other = tmp_path / "other"
    other.mkdir()
    relocated = other / "relocated.json"
    original.rename(relocated)

    updated = history.relink(entry.record_id, relocated, "示例")

    assert updated.record_id == entry.record_id
    assert updated.path == relocated.resolve()
    assert updated.original_dir == other.resolve()


def test_latest_project_appears_first(tmp_path):
    from services.project_history import ProjectHistory

    history = ProjectHistory(tmp_path / "history.json")
    for name in ("first", "second"):
        path = tmp_path / f"{name}.json"
        path.write_text('{"project_name":"示例","findings":[]}', encoding="utf-8")
        history.record(path, name)

    assert [entry.name for entry in history.entries()] == ["second", "first"]


def test_refresh_does_not_follow_symlink_outside_original_dir(tmp_path):
    from services.project_history import ProjectHistory

    original_dir = tmp_path / "original"
    original_dir.mkdir()
    original = original_dir / "project.json"
    original.write_text('{"project_name":"示例","findings":[]}', encoding="utf-8")
    history = ProjectHistory(tmp_path / "history.json")
    history.record(original, "示例")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    moved = elsewhere / "project.json"
    original.rename(moved)
    try:
        (original_dir / "alias.json").symlink_to(moved)
    except OSError:
        pytest.skip("symlinks are unavailable on this Windows host")

    assert history.refresh()[0].missing is True


def test_unavailable_original_directory_keeps_missing_status(tmp_path, monkeypatch):
    from services.project_history import ProjectHistory

    original = tmp_path / "project.json"
    original.write_text('{"project_name":"示例","findings":[]}', encoding="utf-8")
    history = ProjectHistory(tmp_path / "history.json")
    history.record(original, "示例")
    original.unlink()
    real_glob = Path.glob

    def glob(path, pattern):
        if path == tmp_path:
            raise OSError("directory unavailable")
        return real_glob(path, pattern)

    monkeypatch.setattr(Path, "glob", glob)

    assert history.refresh()[0].missing is True
