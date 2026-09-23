import json
from pathlib import Path

from vuln_manager import FIX_PRIORITIES, RISK_LEVELS

ROOT = Path(__file__).resolve().parents[1]
LIBRARY_PATH = ROOT / "vuln_library" / "default_vulns.json"
REQUIRED_FIELDS = {
    "id",
    "name",
    "risk_level",
    "category",
    "description",
    "verify_steps",
    "verify_result",
    "fix_suggestion",
    "fix_priority",
    "fix_verify",
}
REQUIRED_GENERIC_IDS = {
    "XSS-003",
    "INJECT-001",
    "INJECT-002",
    "XXE-001",
    "SSTI-001",
    "REDIRECT-001",
    "CORS-001",
    "HOST-001",
    "AUTH-002",
    "AUTH-003",
    "AUTH-004",
    "SESSION-001",
    "SESSION-002",
    "JWT-001",
    "COOKIE-001",
    "CLICK-001",
    "HEADER-001",
    "TLS-001",
    "TRANS-001",
    "CONFIG-001",
    "CONFIG-002",
    "SOURCE-001",
    "SOURCEMAP-001",
    "CRED-001",
    "FILE-002",
    "FILE-003",
    "API-001",
    "API-002",
    "API-003",
    "LOGIC-001",
    "RACE-001",
}


def _load_templates():
    data = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    return data["vulnerabilities"]


def test_default_library_templates_are_complete_and_valid():
    templates = _load_templates()
    ids = [template["id"] for template in templates]

    assert len(ids) == len(set(ids))
    for template in templates:
        assert REQUIRED_FIELDS <= template.keys(), template["id"]
        assert all(
            template[field] is not None and str(template[field]).strip()
            for field in REQUIRED_FIELDS
        ), template["id"]
        assert template["risk_level"] in RISK_LEVELS, template["id"]
        assert template["fix_priority"] in FIX_PRIORITIES, template["id"]


def test_default_library_covers_common_web_and_api_findings():
    ids = {template["id"] for template in _load_templates()}

    assert REQUIRED_GENERIC_IDS <= ids


def test_default_results_do_not_claim_unperformed_verification():
    templates = _load_templates()

    assert all(
        not template["verify_result"].startswith("经验证，目标存在")
        for template in templates
    )
