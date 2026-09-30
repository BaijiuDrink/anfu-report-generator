from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QStandardPaths


@dataclass(frozen=True)
class RecentProject:
    record_id: str
    name: str
    path: Path
    original_dir: Path
    digest: str
    last_opened: str

    @property
    def missing(self) -> bool:
        return not self.path.is_file()


class ProjectHistory:
    def __init__(self, index_path: Path | None = None):
        data_dir = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
        self.index_path = Path(index_path or Path(data_dir) / "recent-projects.json")
        self._can_write = True
        self._projects = self._load()

    def _load(self) -> list[RecentProject]:
        if not self.index_path.exists():
            return []
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
            if (
                not isinstance(payload, dict)
                or payload.get("version") != 1
                or not isinstance(payload.get("projects"), list)
            ):
                raise ValueError("Unsupported recent-project index version")
            projects = []
            for item in payload["projects"]:
                path = Path(item["path"])
                original_dir = Path(item["original_dir"])
                if (
                    not path.is_absolute()
                    or not original_dir.is_absolute()
                    or path.parent != original_dir
                ):
                    raise ValueError("Invalid recent-project directory")
                datetime.fromisoformat(item["last_opened"])
                projects.append(
                    RecentProject(
                        record_id=item["record_id"],
                        name=item["name"],
                        path=path,
                        original_dir=original_dir,
                        digest=item["digest"],
                        last_opened=item["last_opened"],
                    )
                )
            return projects
        except (OSError, UnicodeError, ValueError, TypeError, KeyError):
            backup = self.index_path.with_name(
                f"{self.index_path.name}.corrupt-{uuid4().hex}"
            )
            try:
                shutil.copy2(self.index_path, backup)
            except OSError:
                self._can_write = False
            return []

    def _save(self) -> None:
        if not self._can_write:
            raise OSError("history index preserved because backup failed")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "projects": [
                {
                    **asdict(project),
                    "path": str(project.path),
                    "original_dir": str(project.original_dir),
                }
                for project in self._projects
            ],
        }
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.index_path.parent, delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(payload, stream, ensure_ascii=False, indent=2)
            os.replace(temporary, self.index_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def entries(self) -> list[RecentProject]:
        return list(self._projects)

    def get(self, record_id: str) -> RecentProject | None:
        return next(
            (item for item in self._projects if item.record_id == record_id), None
        )

    def forget(self, record_id: str) -> None:
        self._projects = [
            item for item in self._projects if item.record_id != record_id
        ]
        self._save()

    def relink(self, record_id: str, path: Path, name: str) -> RecentProject:
        previous = self.get(record_id)
        if previous is None:
            raise KeyError(record_id)
        path = Path(path).resolve()
        project = replace(
            previous,
            name=name.strip() or path.stem,
            path=path,
            original_dir=path.parent,
            digest=hashlib.sha256(path.read_bytes()).hexdigest(),
            last_opened=datetime.now(timezone.utc).isoformat(),
        )
        self._projects = [project] + [
            item
            for item in self._projects
            if item.record_id != record_id and item.path != path
        ]
        self._save()
        return project

    def record(self, path: Path, name: str) -> RecentProject:
        path = Path(path).resolve()
        previous = next((item for item in self._projects if item.path == path), None)
        project = RecentProject(
            record_id=previous.record_id if previous else str(uuid4()),
            name=name.strip() or path.stem,
            path=path,
            original_dir=path.parent,
            digest=hashlib.sha256(path.read_bytes()).hexdigest(),
            last_opened=datetime.now(timezone.utc).isoformat(),
        )
        self._projects = [project] + [
            item for item in self._projects if item.record_id != project.record_id
        ]
        self._save()
        return project

    def refresh(self) -> list[RecentProject]:
        changed = False
        refreshed = []
        for project in self._projects:
            if not project.missing:
                refreshed.append(project)
                continue
            matches = []
            try:
                for candidate in project.original_dir.glob("*.json"):
                    try:
                        if (
                            candidate.is_symlink()
                            or candidate.resolve().parent
                            != project.original_dir.resolve()
                        ):
                            continue
                        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
                    except OSError:
                        continue
                    if digest == project.digest:
                        matches.append(candidate)
            except OSError:
                matches = []
            if len(matches) == 1:
                project = replace(project, path=matches[0].resolve())
                changed = True
            refreshed.append(project)
        self._projects = refreshed
        if changed:
            self._save()
        return self.entries()
