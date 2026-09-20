from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from report_builder import ReportBuilder
from services.project_store import SCREENSHOT_PATTERN


@dataclass(frozen=True)
class ReportCheck:
    missing_images: list[Path]


class ReportValidationError(ValueError):
    pass


def collect_missing_screenshot_paths(
    findings: list[dict], base_dir: Path | None = None
) -> list[Path]:
    missing = []
    seen = set()
    for finding in findings:
        for match in SCREENSHOT_PATTERN.finditer(finding.get("verify_steps", "") or ""):
            path = Path(match.group(1))
            if not path.is_absolute() and base_dir is not None:
                path = Path(base_dir) / path
            normalized = path.resolve() if path.exists() else path
            usable = path.exists()
            if usable:
                try:
                    with Image.open(path) as image:
                        image.verify()
                except Exception:
                    usable = False
            if not usable and normalized not in seen:
                missing.append(normalized)
                seen.add(normalized)
    return missing


class ReportService:
    def check(self, findings: list[dict], base_dir: Path | None = None) -> ReportCheck:
        if not findings:
            raise ReportValidationError("请先录入至少一个漏洞")
        return ReportCheck(
            missing_images=collect_missing_screenshot_paths(findings, base_dir)
        )

    def generate(
        self,
        project_name: str,
        findings: list[dict],
        output_path: Path,
        base_dir: Path | None = None,
    ) -> ReportCheck:
        check = self.check(findings, base_dir)
        builder = ReportBuilder(project_name=project_name or "渗透测试报告")
        builder.add_summary_section(findings)
        builder.add_findings_section(findings)
        builder.save(str(output_path))
        return check
