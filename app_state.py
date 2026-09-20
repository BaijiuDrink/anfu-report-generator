from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectState:
    project_name: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)
    project_path: Path | None = None
    dirty: bool = False

    def replace(self, project_name, findings, project_path):
        self.project_name = project_name
        self.findings = copy.deepcopy(findings)
        self.project_path = project_path
        self.dirty = False

    def clear(self):
        self.replace("", [], None)

    def mark_dirty(self):
        self.dirty = True

    def mark_clean(self):
        self.dirty = False
