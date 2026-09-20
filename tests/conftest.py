import os

import json

import pytest

from vuln_manager import VulnManager

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def vuln_manager(tmp_path):
    path = tmp_path / "vulns.json"
    path.write_text(
        json.dumps(
            {
                "vulnerabilities": [
                    {
                        "id": "sql-injection",
                        "name": "SQL注入漏洞",
                        "category": "注入",
                        "risk_level": "高危",
                        "fix_priority": "高",
                        "description": "description",
                        "verify_steps": "steps",
                        "verify_result": "result",
                        "impact_scope": "scope",
                        "fix_suggestion": "fix",
                        "fix_verify": "verify",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return VulnManager(path)
