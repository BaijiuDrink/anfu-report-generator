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
