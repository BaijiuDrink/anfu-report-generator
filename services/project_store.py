from __future__ import annotations

import copy
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

SCREENSHOT_PATTERN = re.compile(r"\[截图:\s*(.*?)\]")


@dataclass(frozen=True)
class LoadedProject:
    project_name: str
    findings: list[dict[str, Any]]
    path: Path


class ProjectStore:
    def load(self, path: Path) -> LoadedProject:
        path = Path(path).resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        findings = copy.deepcopy(payload.get("findings", []))
        for finding in findings:
            finding["verify_steps"] = self._replace_paths(
                finding.get("verify_steps", ""),
                lambda value: str(self.resolve_screenshot_path(value, path.parent)),
            )
        return LoadedProject(payload.get("project_name", ""), findings, path)

    def resolve_screenshot_path(
        self, image_path: str, base_dir: Path | None = None
    ) -> Path:
        candidate = Path(image_path)
        if candidate.is_absolute():
            return candidate
        if base_dir is not None:
            resolved = Path(base_dir) / candidate
            if resolved.exists():
                return resolved.resolve()
        return candidate

    @staticmethod
    def _replace_paths(content: str, replace: Callable[[str], str]) -> str:
        return SCREENSHOT_PATTERN.sub(
            lambda match: f"[截图: {replace(match.group(1))}]", content or ""
        )

    def save(self, path: Path, project_name: str, findings: list[dict]) -> None:
        path = Path(path).resolve()
        assets_dir = path.parent / f"{path.stem}_attachments"
        copied_paths: dict[Path, str] = {}
        reserved: dict[Path, Path] = {}

        def copy_attachment(value: str) -> str:
            source = self.resolve_screenshot_path(value)
            if not source.exists():
                return value
            source = source.resolve()
            if source not in copied_paths:
                assets_dir.mkdir(parents=True, exist_ok=True)
                destination = assets_dir / source.name
                stem, suffix = source.stem, source.suffix
                counter = 2
                while destination in reserved and reserved[destination] != source:
                    destination = assets_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                reserved[destination] = source
                if destination.resolve() != source:
                    shutil.copy2(source, destination)
                copied_paths[source] = destination.relative_to(path.parent).as_posix()
            return copied_paths[source]

        portable = copy.deepcopy(findings)
        for finding in portable:
            finding["verify_steps"] = self._replace_paths(
                finding.get("verify_steps", ""), copy_attachment
            )
        payload = {"project_name": project_name, "findings": portable}
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
