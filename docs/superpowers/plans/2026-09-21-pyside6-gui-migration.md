# PySide6 GUI Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Tkinter interface with the approved PySide6 professional workstation UI while preserving project files, vulnerability-library behavior, report output, and high-quality Word/WPS image paste.

**Architecture:** Keep `report_builder.py` and `vuln_manager.py` as the business core. Extract project storage, clipboard decoding, report validation, and logging into focused services, then build PySide6 widgets and pages over a small `ProjectState`. Keep the old `gui_app.py` available while parity is developed; replace it with the PySide6 entry point only after the acceptance suite passes.

**Tech Stack:** Python 3.11+, PySide6 6.x, Pillow, pywin32, python-docx, pytest, pytest-qt, PyInstaller, GitHub Actions on Windows.

**Spec:** `docs/superpowers/specs/2026-09-20-pyside6-gui-migration-design.md`

## Global Constraints

- Support Windows 10 and Windows 11 with Python 3.11 or newer.
- Use `PySide6>=6.8,<7`; do not introduce a database or a general state-management framework.
- Preserve the existing project JSON shape: top-level `project_name` and `findings`.
- Preserve all finding keys: `vuln_id`, `name`, `url`, `network_zone`, `risk_level`, `description`, `verify_steps`, `verify_result`, `fix_suggestion`, `fix_priority`, `fix_verify`, and optional `host_ip`.
- Preserve the existing vulnerability-library JSON and `VulnManager` public behavior.
- Keep `report_builder.py` report content and ordering unchanged.
- Store original pasted images on disk; use scaled images only for GUI previews.
- Keep screenshot markers in the persisted form `[截图: path]`.
- Do not implement the later backlog: project home, recent projects, automatic save, backups, or report-template settings.
- Do not expand the CLI; `report_generator.py` remains importable and behavior-compatible.
- Use UTF-8 for project and library JSON files.

## Review Focus

- Word/WPS clipboard data containing HTML plus DIB/EMF images must preserve text-image order and reject blank candidates; Task 3 and Task 4 pin this behavior.
- Two source images with the same basename must receive distinct attachment destinations without overwriting either image; Task 2 pins this behavior.
- Missing or corrupt evidence images must keep their marker visible and produce a pre-generation warning instead of disappearing; Task 4 and Task 8 pin this behavior.
- Switching findings, pages, projects, or closing the window with unsaved edits must offer Save, Discard, and Cancel and honor Cancel; Task 6 and Task 9 pin this behavior.
- Repeatedly loading, pasting, and clearing large images must release preview references while retaining original files and report quality; Task 4 pins resource ownership and Task 10 includes the Windows memory acceptance run.

---

### Task 1: PySide6 Test Foundation and Project State

**Files:**
- Create: `app_state.py`
- Create: `tests/conftest.py`
- Create: `tests/test_app_state.py`
- Create: `requirements-dev.txt`
- Modify: `requirements.txt`
- Modify: `.github/workflows/ci.yml`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Existing finding dictionaries.
- Produces: `ProjectState.replace(project_name: str, findings: list[dict], project_path: Path | None) -> None`, `ProjectState.clear() -> None`, `ProjectState.mark_dirty() -> None`, and `ProjectState.mark_clean() -> None`.

- [ ] **Step 1: Write the failing state tests**

```python
# tests/test_app_state.py
from pathlib import Path

from app_state import ProjectState


def test_replace_deep_copies_findings_and_marks_clean():
    source = [{"name": "SQL注入", "url": "https://example.test"}]
    state = ProjectState()

    state.replace("示例项目", source, Path("project.json"))
    source[0]["name"] = "changed"

    assert state.project_name == "示例项目"
    assert state.findings[0]["name"] == "SQL注入"
    assert state.project_path == Path("project.json")
    assert state.dirty is False


def test_clear_restores_empty_clean_state():
    state = ProjectState(project_name="x", findings=[{"name": "x"}], dirty=True)
    state.clear()
    assert state.project_name == ""
    assert state.findings == []
    assert state.project_path is None
    assert state.dirty is False
```

- [ ] **Step 2: Run the state tests and verify the missing module failure**

Run: `python -m pytest tests/test_app_state.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'app_state'`.

- [ ] **Step 3: Implement the minimal state object**

```python
# app_state.py
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
```

- [ ] **Step 4: Configure headless Qt tests and pinned dependencies**

Create the test bootstrap before importing PySide6:

```python
# tests/conftest.py
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

Add `PySide6>=6.8,<7` to `requirements.txt`. Create `requirements-dev.txt`:

```text
-r requirements.txt
pytest>=8,<9
pytest-qt>=4.4,<5
pytest-cov>=5,<7
black>=24,<27
flake8>=7,<8
pyinstaller>=6.8,<7
psutil>=6,<8
```

Add `.superpowers/` to `.gitignore`. Change CI installation to `pip install -r requirements-dev.txt`, set `QT_QPA_PLATFORM: offscreen`, and add `python -m pytest -q` before the import smoke test.

- [ ] **Step 5: Run foundation checks**

Run:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests/test_app_state.py -q
python -m black --check --diff app_state.py tests
python -m flake8 app_state.py tests --max-line-length=120 --extend-ignore=E501,E402,E203,F401,F541
```

Expected: all commands exit `0`.

- [ ] **Step 6: Commit the foundation**

```powershell
git add app_state.py tests/conftest.py tests/test_app_state.py requirements.txt requirements-dev.txt .github/workflows/ci.yml .gitignore
git commit -m "build: add PySide6 test foundation"
```

### Task 2: Compatible Project Storage Service

**Files:**
- Create: `services/__init__.py`
- Create: `services/project_store.py`
- Create: `tests/services/test_project_store.py`

**Interfaces:**
- Consumes: Finding dictionaries and screenshot markers.
- Produces: `LoadedProject`, `ProjectStore.load(path: Path) -> LoadedProject`, `ProjectStore.save(path: Path, project_name: str, findings: list[dict]) -> None`, and `ProjectStore.resolve_screenshot_path(image_path: str, base_dir: Path | None = None) -> Path`.

- [ ] **Step 1: Write project compatibility and collision tests**

```python
# tests/services/test_project_store.py
import json
from pathlib import Path

from services.project_store import ProjectStore


def test_load_resolves_relative_screenshot_paths(tmp_path):
    image = tmp_path / "demo_attachments" / "proof.png"
    image.parent.mkdir()
    image.write_bytes(b"png")
    project = tmp_path / "demo.json"
    project.write_text(json.dumps({
        "project_name": "demo",
        "findings": [{"name": "x", "verify_steps": "[截图: demo_attachments/proof.png]"}],
    }), encoding="utf-8")

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

    ProjectStore().save(output, "customer", [
        {"name": "one", "verify_steps": f"[截图: {first}]"},
        {"name": "two", "verify_steps": f"[截图: {second}]"},
    ])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "customer_attachments/proof.png" in payload["findings"][0]["verify_steps"]
    assert "customer_attachments/proof_2.png" in payload["findings"][1]["verify_steps"]
    assert (tmp_path / "customer_attachments" / "proof.png").read_bytes() == b"first"
    assert (tmp_path / "customer_attachments" / "proof_2.png").read_bytes() == b"second"
```

- [ ] **Step 2: Run the storage tests and verify failure**

Run: `python -m pytest tests/services/test_project_store.py -q`

Expected: FAIL because `services.project_store` does not exist.

- [ ] **Step 3: Implement compatible load/save behavior**

```python
# services/project_store.py
from __future__ import annotations

import copy
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

    def resolve_screenshot_path(self, image_path: str, base_dir: Path | None = None) -> Path:
        candidate = Path(image_path)
        if candidate.is_absolute():
            return candidate
        if base_dir is not None:
            resolved = Path(base_dir) / candidate
            if resolved.exists():
                return resolved.resolve()
        return candidate

    def _replace_paths(self, content, replace):
        return SCREENSHOT_PATTERN.sub(lambda match: f"[截图: {replace(match.group(1))}]", content or "")

    def save(self, path, project_name, findings):
        path = Path(path).resolve()
        assets_dir = path.parent / f"{path.stem}_attachments"
        copied_paths = {}
        reserved = {}

        def copy_attachment(value):
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
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
```

Preserve a missing source path in its marker instead of deleting it.

- [ ] **Step 4: Add malformed and missing-image coverage**

Add tests asserting invalid JSON raises `json.JSONDecodeError` without modifying an existing `ProjectState`, and a missing screenshot marker survives a save unchanged.

- [ ] **Step 5: Run and commit the storage service**

Run: `python -m pytest tests/services/test_project_store.py -q`

Expected: PASS.

```powershell
git add services/__init__.py services/project_store.py tests/services/test_project_store.py
git commit -m "refactor: extract compatible project storage"
```

### Task 3: Clipboard and Image Service

**Files:**
- Create: `services/clipboard_service.py`
- Create: `tests/services/test_clipboard_service.py`

**Interfaces:**
- Consumes: `QMimeData`, Windows clipboard formats, and Pillow images.
- Produces: `ClipboardSegment = str | Image.Image`, `ClipboardService.read_segments(mime_data: QMimeData | None = None) -> list[ClipboardSegment]`, `flatten_transparency(image: Image.Image) -> Image.Image`, and `save_original_image(image: Image.Image, directory: Path) -> Path`.

- [ ] **Step 1: Write pure image-selection and HTML-order tests**

```python
# tests/services/test_clipboard_service.py
import base64
import io

from PIL import Image

from services.clipboard_service import (
    flatten_transparency,
    image_has_visible_content,
    parse_html_clipboard,
    prefer_best_images,
)


def png_data_uri(size, color):
    image = Image.new("RGBA", size, color)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def test_html_parser_preserves_text_image_text_order():
    html = f"Start<!--StartFragment-->before<img src='{png_data_uri((20, 10), (255, 0, 0, 255))}'>after<!--EndFragment-->"
    segments = parse_html_clipboard(html.encode("utf-8"))
    assert segments[0] == "before"
    assert isinstance(segments[1], Image.Image)
    assert segments[2] == "after"


def test_blank_candidate_is_rejected_and_higher_resolution_is_preferred():
    blank = Image.new("RGBA", (100, 100), (255, 255, 255, 0))
    low = Image.new("RGB", (100, 50), "red")
    high = Image.new("RGB", (1000, 500), "red")
    assert image_has_visible_content(blank) is False
    selected = prefer_best_images([low], [blank, high])
    assert selected[0].size == (1000, 500)


def test_flatten_transparency_returns_opaque_rgb():
    source = Image.new("RGBA", (4, 4), (255, 0, 0, 128))
    assert flatten_transparency(source).mode == "RGB"
```

- [ ] **Step 2: Run tests and verify missing module failure**

Run: `python -m pytest tests/services/test_clipboard_service.py -q`

Expected: FAIL because `services.clipboard_service` does not exist.

- [ ] **Step 3: Move the proven decoding algorithms into the service**

Port these existing behaviors from `gui_app.py` without changing their selection rules:

```python
ClipboardSegment = str | Image.Image


class ClipboardService:
    def read_segments(self, mime_data=None):
        segments = self._read_qt_mime(mime_data)
        windows_candidates = self._read_windows_formats()
        if segments:
            return prefer_best_images(segments, windows_candidates)
        return self._best_visible_candidate(windows_candidates)

    def save_original_image(self, image, directory):
        directory.mkdir(parents=True, exist_ok=True)
        filename = datetime.now().strftime("paste_%Y%m%d_%H%M%S_%f.png")
        path = directory / filename
        flatten_transparency(image).save(path, "PNG")
        return path
```

Implement Qt MIME priority as image, HTML, then text. Keep the current PNG, DIB, DIBV5, enhanced-metafile, HTML data URI, and Word temporary-file paths. Ensure every `OpenClipboard()` has a `finally: CloseClipboard()` path and conversion failures are logged, not raised into the editor.

- [ ] **Step 4: Add mocked Word fallback tests**

Mock `win32clipboard` so an HTML fragment with a blank preview plus a high-resolution DIB/PNG candidate returns the high-resolution candidate in the HTML image position. Add a test that `CloseClipboard()` is called when format decoding raises.

- [ ] **Step 5: Run and commit clipboard extraction**

Run: `python -m pytest tests/services/test_clipboard_service.py -q`

Expected: PASS.

```powershell
git add services/clipboard_service.py tests/services/test_clipboard_service.py
git commit -m "refactor: extract clipboard image handling"
```

### Task 4: Rich Evidence Editor

**Files:**
- Create: `ui/__init__.py`
- Create: `ui/widgets/__init__.py`
- Create: `ui/widgets/evidence_editor.py`
- Create: `tests/ui/test_evidence_editor.py`

**Interfaces:**
- Consumes: `ClipboardService` and screenshot-marker text.
- Produces: `EvidenceEditor.set_marker_text(content: str, base_dir: Path | None = None) -> None`, `EvidenceEditor.marker_text() -> str`, `EvidenceEditor.paste_segments(segments: list[ClipboardSegment]) -> None`, `EvidenceEditor.image_paths() -> list[Path]`, `EvidenceEditor.missing_images() -> list[Path]`, and `EvidenceEditor.preview_resource_count() -> int`.

- [ ] **Step 1: Write GUI tests for ordering, original quality, and cleanup**

```python
# tests/ui/test_evidence_editor.py
from PIL import Image

from ui.widgets.evidence_editor import EvidenceEditor


def test_paste_preserves_text_image_marker_order_and_original_size(qtbot, tmp_path):
    editor = EvidenceEditor(tmp_path)
    qtbot.addWidget(editor)
    image = Image.new("RGB", (2400, 1200), "red")

    editor.paste_segments(["before", image, "after"])
    content = editor.marker_text()

    assert content.index("before") < content.index("[截图:") < content.index("after")
    saved_path = editor.image_paths()[0]
    with Image.open(saved_path) as saved:
        assert saved.size == (2400, 1200)


def test_missing_image_marker_remains_visible(qtbot, tmp_path):
    editor = EvidenceEditor(tmp_path)
    qtbot.addWidget(editor)
    editor.set_marker_text("step\n[截图: missing.png]", tmp_path)
    assert "[截图: missing.png]" in editor.marker_text()
    assert editor.missing_images() == [tmp_path / "missing.png"]


def test_clear_releases_preview_references(qtbot, tmp_path):
    editor = EvidenceEditor(tmp_path)
    qtbot.addWidget(editor)
    editor.paste_segments([Image.new("RGB", (2000, 1000), "blue")])
    assert editor.preview_resource_count() == 1
    editor.clear()
    assert editor.preview_resource_count() == 0
```

- [ ] **Step 2: Run tests and verify missing widget failure**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/ui/test_evidence_editor.py -q`

Expected: FAIL because `ui.widgets.evidence_editor` does not exist.

- [ ] **Step 3: Implement marker-compatible rich text insertion**

```python
class EvidenceEditor(QTextEdit):
    def __init__(self, screenshot_dir, clipboard_service=None, parent=None):
        super().__init__(parent)
        self.screenshot_dir = Path(screenshot_dir)
        self.clipboard_service = clipboard_service or ClipboardService()
        self._image_paths = []
        self._preview_urls = set()
        self._missing_paths = []

    def insertFromMimeData(self, source):
        segments = self.clipboard_service.read_segments(source)
        if segments:
            self.paste_segments(segments)
            return
        super().insertFromMimeData(source)

    def marker_text(self):
        return self.toPlainText().replace("\ufffc", "").strip()

    def image_paths(self):
        return list(self._image_paths)

    def missing_images(self):
        return list(self._missing_paths)

    def preview_resource_count(self):
        return len(self._preview_urls)
```

For each image, call `save_original_image()`, append the returned path to `_image_paths`, scale a separate `QImage` preview to at most `1000x700` with smooth transformation, add it as a `QTextDocument.ImageResource`, insert it, then insert the marker line. `set_marker_text()` parses markers in sequence and inserts a preview before each existing marker. Override `clear()` to clear the document, `_image_paths`, `_preview_urls`, and `_missing_paths`.

- [ ] **Step 4: Add repeated replacement coverage**

Add a test that calls `set_marker_text()` with five images, replaces it with plain text, and confirms `preview_resource_count() == 0` while all five source files still exist.

- [ ] **Step 5: Run and commit the evidence editor**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/ui/test_evidence_editor.py -q`

Expected: PASS.

```powershell
git add ui tests/ui/test_evidence_editor.py
git commit -m "feat: add rich evidence editor"
```

### Task 5: Finding Editor Form

**Files:**
- Create: `ui/widgets/finding_editor.py`
- Create: `tests/ui/test_finding_editor.py`

**Interfaces:**
- Consumes: Finding dictionaries and `EvidenceEditor`.
- Produces: `FindingEditor.set_finding(finding: dict | None) -> None`, `FindingEditor.finding_data() -> dict`, `FindingEditor.clear_form() -> None`, `FindingEditor.is_dirty() -> bool`, `FindingEditor.mark_clean() -> None`, and signal `dirtyChanged(bool)`.

- [ ] **Step 1: Write default, round-trip, and validation tests**

```python
# tests/ui/test_finding_editor.py
import pytest

from ui.widgets.finding_editor import FindingEditor, FindingValidationError


def test_defaults_and_round_trip(qtbot, tmp_path):
    editor = FindingEditor(tmp_path)
    qtbot.addWidget(editor)
    editor.set_finding({"vuln_id": "oauth", "name": "凭证泄露", "url": "a\nb"})
    result = editor.finding_data()
    assert result["vuln_id"] == "oauth"
    assert result["name"] == "凭证泄露"
    assert result["url"] == "a\nb"
    assert result["network_zone"] == "互联网"
    assert result["risk_level"] == "中危"
    assert result["fix_priority"] == "高"


def test_name_is_required(qtbot, tmp_path):
    editor = FindingEditor(tmp_path)
    qtbot.addWidget(editor)
    with pytest.raises(FindingValidationError, match="漏洞名称不能为空"):
        editor.finding_data()
```

- [ ] **Step 2: Run tests and verify missing widget failure**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/ui/test_finding_editor.py -q`

Expected: FAIL because `ui.widgets.finding_editor` does not exist.

- [ ] **Step 3: Build the grouped scrollable form**

Use a `QScrollArea` with one form widget. Use `QLineEdit` for `name`; `QPlainTextEdit` for `url`, `description`, `verify_result`, `fix_suggestion`, and `fix_verify`; `QButtonGroup` radio controls for zone, risk, and priority; and `EvidenceEditor` for `verify_steps`.

```python
FIELD_DEFAULTS = {
    "network_zone": "互联网",
    "risk_level": "中危",
    "fix_priority": "高",
}


class FindingValidationError(ValueError):
    pass


def finding_data(self):
    name = self.name_edit.text().strip()
    if not name:
        raise FindingValidationError("漏洞名称不能为空")
    return {
        "name": name,
        "url": self.url_edit.toPlainText().strip(),
        "network_zone": self.zone_group.checkedButton().property("value"),
        "risk_level": self.risk_group.checkedButton().property("value"),
        "description": self.description_edit.toPlainText().strip(),
        "verify_steps": self.evidence_edit.marker_text(),
        "verify_result": self.verify_result_edit.toPlainText().strip(),
        "fix_suggestion": self.fix_suggestion_edit.toPlainText().strip(),
        "fix_priority": self.priority_group.checkedButton().property("value"),
        "fix_verify": self.fix_verify_edit.toPlainText().strip(),
        "vuln_id": self.vuln_id,
    }
```

Connect every field change to one dirty-state setter, but block signals during `set_finding()` and `clear_form()`.

- [ ] **Step 4: Test dirty-state boundaries**

Add tests proving `set_finding()` and `mark_clean()` are clean, user text edits mark dirty, and `clear_form()` restores defaults without emitting a false dirty event.

- [ ] **Step 5: Run and commit the finding editor**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/ui/test_finding_editor.py -q`

Expected: PASS.

```powershell
git add ui/widgets/finding_editor.py tests/ui/test_finding_editor.py
git commit -m "feat: add PySide6 finding editor"
```

### Task 6: Findings Workspace and Batch Entry

**Files:**
- Create: `ui/pages/__init__.py`
- Create: `ui/pages/findings_page.py`
- Create: `ui/dialogs/__init__.py`
- Create: `ui/dialogs/batch_add_dialog.py`
- Create: `tests/ui/test_findings_page.py`
- Modify: `tests/conftest.py`

**Interfaces:**
- Consumes: `ProjectState`, `FindingEditor`, `VulnManager`, and `batch_create_findings()`.
- Produces: `FindingsPage.set_state(state: ProjectState) -> None`, `FindingsPage.save_current() -> bool`, `FindingsPage.request_selection(index: int) -> bool`, signal `stateChanged()`, and signal `addFromLibraryRequested()`.

- [ ] **Step 1: Add an isolated vulnerability-library fixture**

Append this fixture to `tests/conftest.py`; it must never modify `vuln_library/default_vulns.json`:

```python
import json

import pytest

from vuln_manager import VulnManager


@pytest.fixture
def vuln_manager(tmp_path):
    path = tmp_path / "vulns.json"
    path.write_text(json.dumps({"vulnerabilities": [{
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
    }]}, ensure_ascii=False), encoding="utf-8")
    return VulnManager(path)
```

- [ ] **Step 2: Write action and unsaved-selection tests**

```python
# tests/ui/test_findings_page.py
from app_state import ProjectState
from ui.pages.findings_page import FindingsPage


def make_state():
    return ProjectState(findings=[
        {"name": "one", "url": "a", "network_zone": "互联网", "risk_level": "中危"},
        {"name": "two", "url": "b", "network_zone": "内网", "risk_level": "高危"},
    ])


def test_copy_move_and_search(qtbot, tmp_path, vuln_manager):
    page = FindingsPage(tmp_path, vuln_manager)
    qtbot.addWidget(page)
    state = make_state()
    page.set_state(state)
    page.copy_finding(0)
    assert state.findings[1]["name"] == "one (副本)"
    page.move_finding(1, 1)
    assert state.findings[2]["name"] == "one (副本)"
    page.set_search_text("two")
    assert page.visible_finding_names() == ["two"]


def test_cancel_keeps_current_selection_and_edits(qtbot, tmp_path, vuln_manager, monkeypatch):
    page = FindingsPage(tmp_path, vuln_manager)
    qtbot.addWidget(page)
    page.set_state(make_state())
    page.request_selection(0)
    page.editor.name_edit.setText("edited")
    monkeypatch.setattr(page, "confirm_unsaved", lambda: "cancel")
    assert page.request_selection(1) is False
    assert page.current_index == 0
    assert page.editor.name_edit.text() == "edited"
```

- [ ] **Step 3: Run tests and verify missing page failure**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/ui/test_findings_page.py -q`

Expected: FAIL because `ui.pages.findings_page` does not exist.

- [ ] **Step 4: Implement the splitter workspace and model actions**

Use a horizontal `QSplitter`. The left pane contains search, New Finding, Add from Library, Batch Entry, and a `QListView` backed by a small `QAbstractListModel` over `state.findings`. The right pane contains `FindingEditor` plus Clear Form and Save Finding.

Implement copy with `copy.deepcopy()`, the existing `(副本)` suffix rule, bounds-checked move, confirmation-gated delete, and search over name, URL, and network zone. Every list mutation calls `state.mark_dirty()` and emits `stateChanged`.

Implement `confirm_unsaved()` returning exactly `"save"`, `"discard"`, or `"cancel"`. `request_selection()` must stop on failed validation or Cancel.

- [ ] **Step 5: Implement and test batch entry**

`BatchAddDialog` contains vulnerability ID, network zone, one-host-per-line input, and optional custom name. On accept it calls:

```python
batch_create_findings(
    vuln_manager,
    vuln_id=vuln_id,
    hosts=hosts,
    network_zone=network_zone,
    custom_name=custom_name or None,
)
```

Add tests for missing ID, empty host list, unknown ID, blank lines, and successful append of one finding per nonblank host.

- [ ] **Step 6: Run and commit the findings workspace**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/ui/test_findings_page.py -q`

Expected: PASS.

```powershell
git add ui/pages ui/dialogs/batch_add_dialog.py tests/ui/test_findings_page.py tests/conftest.py
git commit -m "feat: add findings workspace"
```

### Task 7: Vulnerability Library Page and Picker

**Files:**
- Create: `ui/pages/library_page.py`
- Create: `ui/dialogs/library_picker.py`
- Create: `ui/dialogs/vuln_edit_dialog.py`
- Create: `tests/ui/test_library_ui.py`

**Interfaces:**
- Consumes: `VulnManager` and its existing dictionaries.
- Produces: `LibraryPage.refresh() -> None`, `LibraryPicker.selected_template() -> dict | None`, and `VulnEditDialog.result_data() -> dict | None`.

- [ ] **Step 1: Write search, picker, and edit-persistence tests**

```python
# tests/ui/test_library_ui.py
from ui.dialogs.library_picker import LibraryPicker
from ui.pages.library_page import LibraryPage


def test_picker_filters_by_keyword_and_category(qtbot, vuln_manager):
    picker = LibraryPicker(vuln_manager)
    qtbot.addWidget(picker)
    picker.set_keyword("SQL")
    assert all("sql" in item["name"].lower() or "sql" in item["id"].lower() for item in picker.visible_templates())


def test_library_edit_writes_through_manager(qtbot, vuln_manager):
    page = LibraryPage(vuln_manager)
    qtbot.addWidget(page)
    vuln_id = vuln_manager.list_all()[0]["id"]
    page.save_template(vuln_id, {"name": "更新后的名称", "impact_scope": "互联网系统"})
    saved = vuln_manager.get_by_id(vuln_id)
    assert saved["name"] == "更新后的名称"
    assert saved["impact_scope"] == "互联网系统"
```

- [ ] **Step 2: Run tests and verify missing UI failure**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/ui/test_library_ui.py -q`

Expected: FAIL because the library UI modules do not exist.

- [ ] **Step 3: Implement the independent library page**

Use a searchable/filterable list on the left and a read-only preview on the right. Keep Add, Edit, and Delete actions. `VulnEditDialog` exposes the exact library fields `id`, `name`, `category`, `risk_level`, `fix_priority`, `description`, `verify_steps`, `verify_result`, `impact_scope`, `fix_suggestion`, and `fix_verify`.

Use `VulnManager.add()`, `update()`, and `delete()` directly and refresh after each successful mutation. Show manager `ValueError` messages without closing the edit dialog.

- [ ] **Step 4: Implement the searchable picker dialog**

The picker combines keyword search and category filtering, shows the full template preview, disables Add until a row is selected, and returns a deep copy from `VulnManager.get_by_id()`.

Connect `FindingsPage.addFromLibraryRequested` so an accepted template calls `create_finding(vuln_manager, vuln_id=template["id"])`, appends the result, selects it, marks the project dirty, and focuses the address field.

- [ ] **Step 5: Run and commit the library UI**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/ui/test_library_ui.py tests/ui/test_findings_page.py -q`

Expected: PASS.

```powershell
git add ui/pages/library_page.py ui/dialogs/library_picker.py ui/dialogs/vuln_edit_dialog.py tests/ui/test_library_ui.py ui/pages/findings_page.py
git commit -m "feat: add vulnerability library workflow"
```

### Task 8: Report Service and Missing-Evidence Warnings

**Files:**
- Create: `services/report_service.py`
- Create: `tests/services/test_report_service.py`

**Interfaces:**
- Consumes: Existing `ReportBuilder` and finding dictionaries.
- Produces: `ReportCheck`, `ReportService.check(findings: list[dict], base_dir: Path | None = None) -> ReportCheck`, and `ReportService.generate(project_name: str, findings: list[dict], output_path: Path, base_dir: Path | None = None) -> ReportCheck`.

- [ ] **Step 1: Write validation and builder-call tests**

```python
# tests/services/test_report_service.py
from pathlib import Path

import pytest

from services.report_service import ReportService, ReportValidationError


def test_empty_findings_are_rejected():
    with pytest.raises(ReportValidationError, match="请先录入至少一个漏洞"):
        ReportService().check([])


def test_missing_images_are_reported_but_marker_is_preserved(tmp_path):
    finding = {"name": "x", "verify_steps": "[截图: missing.png]"}
    check = ReportService().check([finding], base_dir=tmp_path)
    assert check.missing_images == [tmp_path / "missing.png"]
    assert finding["verify_steps"] == "[截图: missing.png]"


def test_generate_calls_existing_builder_in_order(tmp_path, monkeypatch):
    calls = []
    class FakeBuilder:
        def __init__(self, project_name): calls.append(("init", project_name))
        def add_summary_section(self, findings): calls.append(("summary", findings))
        def add_findings_section(self, findings): calls.append(("details", findings))
        def save(self, path): calls.append(("save", path))
    monkeypatch.setattr("services.report_service.ReportBuilder", FakeBuilder)
    findings = [{"name": "x", "verify_steps": ""}]
    output = tmp_path / "report.docx"
    ReportService().generate("demo", findings, output)
    assert [item[0] for item in calls] == ["init", "summary", "details", "save"]
```

- [ ] **Step 2: Run tests and verify missing service failure**

Run: `python -m pytest tests/services/test_report_service.py -q`

Expected: FAIL because `services.report_service` does not exist.

- [ ] **Step 3: Implement validation and unchanged builder orchestration**

```python
@dataclass(frozen=True)
class ReportCheck:
    missing_images: list[Path]


class ReportValidationError(ValueError):
    pass


class ReportService:
    def check(self, findings, base_dir=None):
        if not findings:
            raise ReportValidationError("请先录入至少一个漏洞")
        missing = collect_missing_screenshot_paths(findings, base_dir)
        return ReportCheck(missing_images=missing)

    def generate(self, project_name, findings, output_path, base_dir=None):
        check = self.check(findings, base_dir)
        builder = ReportBuilder(project_name=project_name or "渗透测试报告")
        builder.add_summary_section(findings)
        builder.add_findings_section(findings)
        builder.save(str(output_path))
        return check
```

- [ ] **Step 4: Run regression tests against a real DOCX**

Create a test with one finding and one PNG, generate a DOCX, reopen it with `python-docx`, and assert the finding name, URL, description, and image relationship exist.

- [ ] **Step 5: Run and commit the report service**

Run: `python -m pytest tests/services/test_report_service.py -q`

Expected: PASS.

```powershell
git add services/report_service.py tests/services/test_report_service.py
git commit -m "refactor: add report generation service"
```

### Task 9: Main Window, Project Lifecycle, Theme, and Logging

**Files:**
- Create: `services/logging_setup.py`
- Create: `ui/theme.py`
- Create: `ui/main_window.py`
- Create: `tests/ui/test_main_window.py`

**Interfaces:**
- Consumes: `ProjectState`, `ProjectStore`, `ReportService`, `FindingsPage`, `LibraryPage`, and `VulnManager`.
- Produces: `MainWindow(state: ProjectState | None = None, project_store: ProjectStore | None = None, report_service: ReportService | None = None, vuln_manager: VulnManager | None = None, screenshots_dir: Path | None = None)`, `MainWindow.new_project()`, `MainWindow.open_project(path: Path | None = None)`, `MainWindow.save_project(path: Path | None = None) -> bool`, `MainWindow.generate_report(path: Path | None = None) -> bool`, and `MainWindow.confirm_project_change() -> str`.

- [ ] **Step 1: Write lifecycle and unsaved-guard tests**

```python
# tests/ui/test_main_window.py
import json

import pytest

from app_state import ProjectState
from services.project_store import ProjectStore
from services.report_service import ReportService
from ui.main_window import MainWindow


@pytest.fixture
def window_deps(tmp_path, vuln_manager):
    project_path = tmp_path / "next.json"
    project_path.write_text(json.dumps({"project_name": "next", "findings": []}), encoding="utf-8")
    deps = {
        "state": ProjectState(),
        "project_store": ProjectStore(),
        "report_service": ReportService(),
        "vuln_manager": vuln_manager,
        "screenshots_dir": tmp_path / "screenshots",
    }
    return deps, project_path


def test_cancel_prevents_project_replacement(qtbot, window_deps, monkeypatch):
    deps, project_path = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    window.state.replace("old", [{"name": "old"}], None)
    window.state.mark_dirty()
    monkeypatch.setattr(window, "confirm_project_change", lambda: "cancel")
    assert window.open_project(project_path) is False
    assert window.state.project_name == "old"


def test_failed_open_preserves_current_state(qtbot, window_deps, monkeypatch):
    deps, project_path = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    window.state.replace("old", [{"name": "old"}], None)
    monkeypatch.setattr(deps["project_store"], "load", lambda path: (_ for _ in ()).throw(ValueError("broken")))
    assert window.open_project(project_path) is False
    assert window.state.project_name == "old"


def test_navigation_shows_findings_and_library_pages(qtbot, window_deps):
    deps, _ = window_deps
    window = MainWindow(**deps)
    qtbot.addWidget(window)
    window.show_library_page()
    assert window.page_stack.currentWidget() is window.library_page
    window.show_findings_page()
    assert window.page_stack.currentWidget() is window.findings_page
```

- [ ] **Step 2: Run tests and verify missing window failure**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/ui/test_main_window.py -q`

Expected: FAIL because `ui.main_window` does not exist.

- [ ] **Step 3: Build the approved professional workstation shell**

Use a top bar with project name plus New, Open, Save, and Generate Report. Use a dark navy sidebar with Findings and Vulnerability Library, a `QStackedWidget` page area, and a status bar. Apply one light QSS theme from `ui/theme.py`; keep risk colors semantic and reserve blue for selection and primary actions.

The window owns one `ProjectState`. Opening parses into a temporary `LoadedProject` and calls `state.replace()` only after success. Saving commits the active editor first, writes through `ProjectStore`, updates `project_path`, marks clean, and reports success in the status bar.

Preserve current guards: saving with no findings shows `没有可保存的漏洞记录`, and generating with no findings shows `请先录入至少一个漏洞`. Before generation, show one summary dialog when `ReportService.check()` reports missing images; Continue generates with available evidence and Cancel leaves the project untouched.

- [ ] **Step 4: Implement unsaved guards and failure logging**

```python
def confirm_project_change(self):
    if not self.state.dirty and not self.findings_page.editor.is_dirty():
        return "discard"
    box = QMessageBox(self)
    box.setWindowTitle("未保存的更改")
    box.setText("当前项目存在未保存内容。")
    save = box.addButton("保存", QMessageBox.AcceptRole)
    discard = box.addButton("放弃", QMessageBox.DestructiveRole)
    cancel = box.addButton("取消", QMessageBox.RejectRole)
    box.exec()
    return "save" if box.clickedButton() is save else "discard" if box.clickedButton() is discard else "cancel"
```

Use `RotatingFileHandler(maxBytes=1_000_000, backupCount=3, encoding="utf-8")` in the user data directory. Log tracebacks for project, clipboard, attachment, and report failures; dialogs show only concise actionable text. A failed operation must not clear state.

- [ ] **Step 5: Add close, page-switch, and Save-failure tests**

Use `qtbot` and monkeypatched message boxes to exercise Save, Discard, and Cancel for page switch and close. Mock `ProjectStore.save()` to raise and assert state remains dirty and the window remains open.

- [ ] **Step 6: Run and commit the application shell**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/ui/test_main_window.py tests/ui -q`

Expected: PASS.

```powershell
git add services/logging_setup.py ui/theme.py ui/main_window.py tests/ui/test_main_window.py
git commit -m "feat: add PySide6 application shell"
```

### Task 10: Entrypoint, Legacy Removal, Packaging, Documentation, and Acceptance

**Files:**
- Replace: `gui_app.py`
- Modify: `安服报告生成工具.spec`
- Modify: `README.md`
- Modify: `.github/workflows/ci.yml`
- Create: `tests/test_gui_entrypoint.py`
- Delete after acceptance: Tkinter implementation formerly contained in `gui_app.py`

**Interfaces:**
- Consumes: `ui.main_window.MainWindow` and `services.logging_setup.configure_logging()`.
- Produces: `gui_app.create_application(argv: list[str] | None = None) -> QApplication` and `gui_app.main() -> int`.

- [ ] **Step 1: Write the entrypoint smoke test**

```python
# tests/test_gui_entrypoint.py
from PySide6.QtWidgets import QApplication

import gui_app


def test_create_application_returns_qapplication(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = gui_app.create_application([])
    assert isinstance(app, QApplication)
    assert QApplication.applicationName() == "安服报告工作台"
```

- [ ] **Step 2: Run the smoke test against the old entrypoint**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_gui_entrypoint.py -q`

Expected: FAIL because the Tkinter `gui_app.py` has no `create_application()`.

- [ ] **Step 3: Replace the Tkinter entrypoint after the complete suite is green**

Before replacing it, run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -q
```

Expected: all Tasks 1-9 tests PASS.

Replace `gui_app.py` with:

```python
import sys

from PySide6.QtWidgets import QApplication

from services.logging_setup import configure_logging
from ui.main_window import MainWindow


def create_application(argv=None):
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("安服报告工作台")
    app.setOrganizationName("BaijiuDrink")
    return app


def main():
    configure_logging()
    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

The old Tkinter code remains recoverable in Git history and is not kept as a second shipped UI.

- [ ] **Step 4: Update packaging and CI**

Keep the default vulnerability JSON in `datas` and rely on PyInstaller's shipped PySide6 hooks for Qt modules and platform plugins:

```python
datas = [("vuln_library/default_vulns.json", "vuln_library")]
```

Update the spec entry script to `gui_app.py`, keep `console=False`, and retain the Chinese executable name. Add a CI step:

```yaml
- name: Build Windows executable
  run: pyinstaller --noconfirm --clean "安服报告生成工具.spec"
```

Update README GUI screenshots/features, PySide6 dependency instructions, project-file compatibility, Word/WPS paste behavior, and Windows build command. Label CLI as legacy without deleting `report_generator.py`.

- [ ] **Step 5: Run complete automated verification**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -q
python -m black --check --diff .
python -m flake8 . --max-line-length=120 --extend-ignore=E501,E402,E203,F401,F541
python -m compileall -q gui_app.py app_state.py report_builder.py report_generator.py vuln_manager.py services ui
pyinstaller --noconfirm --clean "安服报告生成工具.spec"
```

Expected: all commands exit `0` and `dist/安服报告生成工具.exe` exists.

- [ ] **Step 6: Perform Windows acceptance checks**

Run the packaged executable on a Windows machine without using the source checkout and record the result of each check in the commit or PR description:

1. Open an existing JSON project and confirm all fields and evidence previews.
2. Edit, copy, reorder, delete, and batch-add findings.
3. Edit and persist a vulnerability-library template.
4. Paste mixed text and images from Microsoft Word and WPS; confirm order and nonblank previews.
5. Paste a single screenshot and multiple images.
6. Save, reopen, and verify portable attachment paths.
7. Generate a DOCX and compare field order/content with the previous release.
8. Confirm DOCX images use original resolution.
9. Paste and clear twenty large images while observing process memory; after clearing and processing events, retained preview references must return to zero and memory must stop growing across repeated cycles.
10. Trigger missing-image, malformed-project, and failed-output-path errors and confirm the current project remains intact.

- [ ] **Step 7: Commit the completed migration**

```powershell
git add gui_app.py "安服报告生成工具.spec" README.md .github/workflows/ci.yml tests/test_gui_entrypoint.py
git commit -m "feat: migrate desktop GUI to PySide6"
```

- [ ] **Step 8: Run final branch review**

Run:

```powershell
git status --short
git diff 7c81f41..HEAD --check
python -m pytest -q
```

Expected: no unintended files, no whitespace errors, and all tests PASS. Request a whole-branch code review focused on project compatibility, Word/WPS paste, unsaved-change guards, report parity, and packaged Windows startup.
