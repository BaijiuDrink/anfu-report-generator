import json
from pathlib import Path

import vuln_manager as vuln_module


def test_frozen_default_library_persists_in_user_data(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled.json"
    bundled.write_text(
        json.dumps(
            {"vulnerabilities": [{"id": "demo", "name": "原名称", "category": "其他"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    user_root = tmp_path / "local-app-data"
    monkeypatch.setenv("LOCALAPPDATA", str(user_root))
    monkeypatch.setattr(vuln_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(vuln_module, "BUNDLED_VULN_LIBRARY", bundled)

    manager = vuln_module.VulnManager()
    manager.update("demo", {"name": "持久化名称"})
    reloaded = vuln_module.VulnManager()

    expected = (
        user_root
        / "BaijiuDrink"
        / "AnfuReportWorkbench"
        / "vuln_library"
        / "default_vulns.json"
    )
    assert Path(manager.library_path) == expected
    assert reloaded.get_by_id("demo")["name"] == "持久化名称"


def test_frozen_library_upgrade_preserves_edits_and_merges_new_defaults(
    tmp_path, monkeypatch
):
    bundled = tmp_path / "bundled.json"
    bundled.write_text(
        json.dumps(
            {
                "vulnerabilities": [
                    {
                        "id": "demo",
                        "name": "默认名称",
                        "category": "其他",
                        "description": "默认描述",
                        "fix_suggestion": "默认建议",
                    },
                    {
                        "id": "new-default",
                        "name": "新增模板",
                        "category": "通用",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    user_root = tmp_path / "local-app-data"
    destination = (
        user_root
        / "BaijiuDrink"
        / "AnfuReportWorkbench"
        / "vuln_library"
        / "default_vulns.json"
    )
    destination.parent.mkdir(parents=True)
    destination.write_text(
        json.dumps(
            {
                "vulnerabilities": [
                    {
                        "id": "demo",
                        "name": "用户自定义名称",
                        "category": "其他",
                        "description": "   ",
                        "fix_suggestion": "用户自定义建议",
                    },
                    {
                        "id": "custom",
                        "name": "用户新增模板",
                        "category": "自定义",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LOCALAPPDATA", str(user_root))
    monkeypatch.setattr(vuln_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(vuln_module, "BUNDLED_VULN_LIBRARY", bundled)

    manager = vuln_module.VulnManager()

    assert manager.get_by_id("demo")["name"] == "用户自定义名称"
    assert manager.get_by_id("demo")["description"] == "默认描述"
    assert manager.get_by_id("demo")["fix_suggestion"] == "用户自定义建议"
    assert manager.get_by_id("new-default")["name"] == "新增模板"
    assert manager.get_by_id("custom")["name"] == "用户新增模板"

    reloaded = vuln_module.VulnManager()

    assert len(reloaded.list_all()) == 3
