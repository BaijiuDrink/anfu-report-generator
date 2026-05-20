import json
import os
import copy

DEFAULT_VULN_LIBRARY = os.path.join(
    os.path.dirname(__file__), "vuln_library", "default_vulns.json"
)

RISK_LEVELS = ["严重", "高危", "中危", "低危", "信息"]
FIX_PRIORITIES = ["紧急", "高", "中", "低"]
NETWORK_ZONES = ["互联网", "内网"]


class VulnManager:
    def __init__(self, library_path=None):
        self.library_path = library_path or DEFAULT_VULN_LIBRARY
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.library_path):
            return {"vulnerabilities": []}
        with open(self.library_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self):
        with open(self.library_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def list_all(self):
        return self.data.get("vulnerabilities", [])

    def search(self, keyword):
        keyword_lower = keyword.lower()
        results = []
        for v in self.data.get("vulnerabilities", []):
            if (
                keyword_lower in v.get("name", "").lower()
                or keyword_lower in v.get("category", "").lower()
                or keyword_lower in v.get("id", "").lower()
            ):
                results.append(v)
        return results

    def get_by_id(self, vuln_id):
        for v in self.data.get("vulnerabilities", []):
            if v.get("id") == vuln_id:
                return copy.deepcopy(v)
        return None

    def add(self, vuln):
        vuln["id"] = vuln.get("id", "").strip()
        if not vuln["id"]:
            raise ValueError("漏洞ID不能为空")
        if self.get_by_id(vuln["id"]):
            raise ValueError(f"漏洞ID [{vuln['id']}] 已存在")
        vuln.setdefault("risk_level", "中危")
        vuln.setdefault("category", "其他")
        vuln.setdefault("description", "")
        vuln.setdefault("verify_steps", "")
        vuln.setdefault("verify_result", "")
        vuln.setdefault("fix_suggestion", "")
        vuln.setdefault("fix_priority", "高")
        vuln.setdefault("fix_verify", "")
        self.data.setdefault("vulnerabilities", []).append(vuln)
        self._save()
        return vuln

    def update(self, vuln_id, updates):
        v = self.get_by_id(vuln_id)
        if not v:
            raise ValueError(f"漏洞ID [{vuln_id}] 不存在")
        allowed_fields = [
            "name",
            "risk_level",
            "category",
            "description",
            "verify_steps",
            "verify_result",
            "fix_suggestion",
            "fix_priority",
            "fix_verify",
        ]
        for field in allowed_fields:
            if field in updates:
                v[field] = updates[field]
        self._save()
        return v

    def delete(self, vuln_id):
        vulns = self.data.get("vulnerabilities", [])
        self.data["vulnerabilities"] = [v for v in vulns if v.get("id") != vuln_id]
        self._save()

    def get_library_path(self):
        return self.library_path

    def get_categories(self):
        cats = set()
        for v in self.data.get("vulnerabilities", []):
            cat = v.get("category", "其他")
            if cat:
                cats.add(cat)
        return sorted(cats)


def _build_finding_from_template(template):
    return {
        "vuln_id": template.get("id"),
        "name": template.get("name", ""),
        "description": template.get("description", ""),
        "risk_level": template.get("risk_level", "中危"),
        "verify_steps": template.get("verify_steps", ""),
        "verify_result": template.get("verify_result", ""),
        "fix_suggestion": template.get("fix_suggestion", ""),
        "fix_priority": template.get("fix_priority", "高"),
        "fix_verify": template.get("fix_verify", ""),
    }


def create_finding(
    vuln_manager,
    vuln_id=None,
    url="",
    custom_name=None,
    custom_description=None,
    custom_risk_level=None,
    custom_fix_suggestion=None,
    verify_steps=None,
    verify_result=None,
    fix_priority=None,
    fix_verify=None,
    network_zone="互联网",
    host_ip="",
):
    finding = {
        "vuln_id": vuln_id,
        "name": custom_name,
        "url": url,
        "risk_level": custom_risk_level,
        "description": custom_description,
        "verify_steps": verify_steps,
        "verify_result": verify_result,
        "fix_suggestion": custom_fix_suggestion,
        "fix_priority": fix_priority,
        "fix_verify": fix_verify,
        "network_zone": network_zone,
        "host_ip": host_ip,
    }
    if vuln_id:
        template = vuln_manager.get_by_id(vuln_id)
        if template:
            if not custom_name:
                finding["name"] = template.get("name", vuln_id)
            if not custom_risk_level:
                finding["risk_level"] = template.get("risk_level", "中危")
            if not custom_description:
                finding["description"] = template.get("description", "")
            if not verify_steps:
                finding["verify_steps"] = template.get("verify_steps", "")
            if not verify_result:
                finding["verify_result"] = template.get("verify_result", "")
            if not custom_fix_suggestion:
                finding["fix_suggestion"] = template.get("fix_suggestion", "")
            if not fix_priority:
                finding["fix_priority"] = template.get("fix_priority", "高")
            if not fix_verify:
                finding["fix_verify"] = template.get("fix_verify", "")
        else:
            print(f"[警告] 漏洞库中未找到ID [{vuln_id}]，将使用自定义信息")
    finding["risk_level"] = finding.get("risk_level") or custom_risk_level or "中危"
    finding["fix_priority"] = finding.get("fix_priority") or fix_priority or "高"
    finding.setdefault("network_zone", network_zone or "互联网")
    finding.setdefault("host_ip", host_ip or "")
    return finding


def batch_create_findings(
    vuln_manager,
    vuln_id,
    hosts,
    network_zone="内网",
    custom_name=None,
    custom_risk_level=None,
    verify_steps=None,
    verify_result=None,
):
    template = vuln_manager.get_by_id(vuln_id)
    if not template:
        raise ValueError(f"漏洞库中未找到ID [{vuln_id}]")

    base = _build_finding_from_template(template)

    findings = []
    for host in hosts:
        host = host.strip()
        if not host:
            continue
        f = copy.deepcopy(base)
        f["name"] = custom_name or base["name"]
        f["risk_level"] = custom_risk_level or base["risk_level"]
        f["url"] = host
        f["host_ip"] = host
        f["network_zone"] = network_zone
        f["vuln_id"] = vuln_id
        if verify_steps:
            f["verify_steps"] = verify_steps
        if verify_result:
            f["verify_result"] = verify_result
        findings.append(f)

    return findings
