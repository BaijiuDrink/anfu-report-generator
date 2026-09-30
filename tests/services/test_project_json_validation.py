import json

import pytest

from services.project_store import ProjectStore


@pytest.mark.parametrize(
    "payload",
    [
        {"unrelated": 1},
        {"project_name": "demo", "findings": "not a list"},
        {"project_name": "demo", "findings": ["not a finding"]},
    ],
)
def test_load_rejects_non_project_json(tmp_path, payload):
    project = tmp_path / "not-project.json"
    project.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="project"):
        ProjectStore().load(project)
