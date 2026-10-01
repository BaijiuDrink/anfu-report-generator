import json

import pytest

from app_state import ProjectState
from services.project_store import ProjectStore


def test_load_resolves_relative_screenshot_paths(tmp_path):
    image = tmp_path / "demo_attachments" / "proof.png"
    image.parent.mkdir()
    image.write_bytes(b"png")
    project = tmp_path / "demo.json"
    project.write_text(
        json.dumps(
            {
                "project_name": "demo",
                "findings": [
                    {
                        "name": "x",
                        "verify_steps": "[截图: demo_attachments/proof.png]",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    loaded = ProjectStore().load(project)
    assert loaded.project_name == "demo"
    assert str(image.resolve()) in loaded.findings[0]["verify_steps"]


def test_save_renames_same_basename_without_overwrite(tmp_path):
    first = tmp_path / "a" / "proof.png"
    second = tmp_path / "b" / "proof.png"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    output = tmp_path / "customer.json"

    ProjectStore().save(
        output,
        "customer",
        [
            {"name": "one", "verify_steps": f"[截图: {first}]"},
            {"name": "two", "verify_steps": f"[截图: {second}]"},
        ],
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "customer_attachments/proof.png" in payload["findings"][0]["verify_steps"]
    assert "customer_attachments/proof_2.png" in payload["findings"][1]["verify_steps"]
    assert (tmp_path / "customer_attachments" / "proof.png").read_bytes() == b"first"
    assert (tmp_path / "customer_attachments" / "proof_2.png").read_bytes() == b"second"


def test_invalid_json_does_not_modify_existing_state(tmp_path):
    state = ProjectState(project_name="current", findings=[{"name": "kept"}])
    broken = tmp_path / "broken.json"
    broken.write_text("{broken", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        ProjectStore().load(broken)

    assert state.project_name == "current"
    assert state.findings == [{"name": "kept"}]


def test_save_preserves_missing_screenshot_marker(tmp_path):
    output = tmp_path / "customer.json"
    marker = "[截图: missing/proof.png]"

    ProjectStore().save(output, "customer", [{"name": "x", "verify_steps": marker}])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["findings"][0]["verify_steps"] == marker


def test_poc_exp_code_survives_project_save_and_load(tmp_path):
    output = tmp_path / "customer.json"
    code = "curl -X POST /test\nif authorized:\n    run_exp()"

    ProjectStore().save(
        output,
        "customer",
        [{"name": "命令执行", "poc_exp": code}],
    )

    loaded = ProjectStore().load(output)

    assert loaded.findings[0]["poc_exp"] == code
