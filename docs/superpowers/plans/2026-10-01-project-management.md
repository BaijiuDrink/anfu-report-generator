# Project Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a styled Project Management page that opens recent JSON projects and recovers same-directory renames without scanning other directories.

**Architecture:** A small application-local history service stores metadata and a file digest, independent of the existing project JSON schema. A dedicated PySide6 page displays records and emits action requests; `MainWindow` owns navigation, file dialogs, project loading, and unsaved-change decisions.

**Tech Stack:** Python 3.11, PySide6, JSON, `hashlib`, `pathlib`, pytest/pytest-qt, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-10-01-project-management-design.md`

## Global Constraints

- Automatically scan only each recorded JSON file's original directory, non-recursively, for `*.json`; never scan another directory or disk.
- Keep project JSON format, `ProjectStore` attachment behavior, report output, and existing GUI fields unchanged.
- Cross-directory recovery is manual through a user-initiated file picker; a missing record reads `JSON 文件已移动`.
- Persist history under Qt's local application-data location, not beside project JSON; use atomic writes.
- Preserve all pre-existing uncommitted work in this worktree. Stage and commit only new-task changes; do not accidentally include earlier UI/POC edits.

## Review Focus

- Two identical JSON files in the original directory: do not guess a replacement; keep the record marked missing (Task 1 test).
- JSON moved to a different directory: do not traverse there, even when the filename matches (Task 1 test).
- A malformed or unreadable sibling JSON: skip it without interrupting history refresh (Task 1 test).
- A corrupt history index: preserve the corrupt bytes in a backup and show an empty, usable list (Task 1 test).
- Unsaved editor changes when opening a history item: Cancel must leave the current project and page unchanged (Task 3 test).

---

### Task 1: Recent-project history service

**Files:** Create `services/project_history.py`; create `tests/services/test_project_history.py`.

**Interfaces:** Produce `RecentProject(record_id: str, name: str, path: Path, original_dir: Path, digest: str, last_opened: str)` with `missing` derived from `path.is_file()`. Produce `ProjectHistory(index_path: Path | None = None)` with `entries() -> list[RecentProject]`, `get(record_id: str) -> RecentProject | None`, `record(path: Path, name: str) -> RecentProject`, `refresh() -> list[RecentProject]`, `relink(record_id: str, path: Path, name: str) -> RecentProject`, and `forget(record_id: str) -> None`.

- [ ] **Step 1: Write failing tests.** `test_record_persists_and_updates` asserts `len(ProjectHistory(index).entries()) == 1` after re-recording one path and verifies the new name. `test_refresh_recovers_same_directory_rename` renames the file, then asserts `history.refresh()[0].path == renamed`. `test_forget_keeps_json` asserts the file still exists after `forget(record_id)`.
- [ ] **Step 2: Run `python -m pytest -q tests/services/test_project_history.py`.** Expect import/API failures.
- [ ] **Step 3: Implement the service.** Use `QStandardPaths.AppLocalDataLocation/recent-projects.json` by default; inject `index_path` in tests. Store schema version 1 and stable `record_id` (UUID only in the index, never project JSON). Hash file bytes; write via temporary file plus `os.replace`.
- [ ] **Step 4: Run the service tests.** Expect all new tests to pass.
- [ ] **Step 5: Add failing edge-case tests.** `test_ambiguous_digest_stays_missing` asserts `entry.missing` with two identical siblings. `test_refresh_never_scans_other_directory` moves the JSON out and asserts `entry.missing`. `test_bad_sibling_does_not_abort_refresh` uses an invalid/unreadable sibling and asserts refresh succeeds. `test_corrupt_index_is_backed_up` asserts empty entries and a backup containing the original bytes.
- [ ] **Step 6: Implement only the missing edge-case behavior and rerun `python -m pytest -q tests/services/test_project_history.py`.** Expect all tests to pass.
- [ ] **Step 7: Commit only the new service and its tests**, after confirming the staged diff excludes prior work.

### Task 2: Project Management page

**Files:** Create `ui/pages/projects_page.py`; create `tests/ui/test_projects_page.py`; modify `ui/theme.py`.

**Interfaces:** Consume `RecentProject`. Produce `ProjectsPage.set_projects(projects: list[RecentProject]) -> None` and signals `openRequested(str)`, `relocateRequested(str)`, `removeRequested(str)`, each emitting a stable `record_id`. The page owns search/filtering and display, not disk access or dialogs.

- [ ] **Step 1: Write failing pytest-qt tests.** `test_project_cards_show_status` asserts the visible name/path/time and exact `JSON 文件已移动` suffix for a missing record. `test_search_filters_cards` asserts only a matching name or path remains. `test_actions_emit_record_id` uses `QSignalSpy` to assert Open, Relocate, and Remove each emit the selected `record_id`. `test_empty_history_state` asserts the empty prompt is shown.
- [ ] **Step 2: Run `python -m pytest -q tests/ui/test_projects_page.py`.** Expect import/API failures.
- [ ] **Step 3: Build the page and add theme rules.** Match the existing warm surface, compact cards, restrained blue actions, and missing-state warning; include an empty-history state. Remove from History must never touch the JSON file.
- [ ] **Step 4: Run the page tests and render a native Windows Qt screenshot of the page at 900x600.** Expect tests to pass and no clipped controls; inspect the full main-window minimum size in Task 3.
- [ ] **Step 5: Commit only new page/test changes.** If `ui/theme.py` still contains earlier uncommitted changes, stage only this task's theme hunks or defer that file's commit; do not stage the whole prior diff.

### Task 3: Main-window integration and release verification

**Files:** Modify `ui/main_window.py`; modify `tests/ui/test_main_window.py`; modify `tests/ui/test_projects_page.py` if an integration assertion belongs there.

**Interfaces:** Consume `ProjectHistory` and `ProjectsPage`. Add optional `project_history: ProjectHistory | None` constructor argument; `show_projects_page() -> bool`, `open_recent_project(record_id: str) -> bool`, `relocate_recent_project(record_id: str, path: Path | None = None) -> bool`, and `remove_recent_project(record_id: str) -> None`. Preserve `open_project(path)` and `save_project(path)` signatures.

- [ ] **Step 1: Write failing integration tests.** Inject a temporary history index in `window_deps`. `test_successful_open_and_save_enter_history` asserts one updated record. `test_recent_open_rechecks_missing_path` renames the JSON in its original directory and asserts the recovered path is loaded. `test_failed_project_action_does_not_record` asserts zero records. `test_recent_open_cancel_preserves_current_project` asserts the old project name/path and page remain after Cancel.
- [ ] **Step 2: Run `python -m pytest -q tests/ui/test_main_window.py`.** Expect new tests to fail for missing navigation/history behavior.
- [ ] **Step 3: Wire the sidebar and page.** Reuse the existing editor-navigation decision for Library and Projects without discarding draft data; refresh history on every page entry. Route historical Open through `open_project`.
- [ ] **Step 4: Add failing Relocate tests.** `test_manual_relocate_updates_record` asserts new path and original directory. `test_name_mismatch_needs_confirmation` asserts a No response leaves the record unchanged. `test_invalid_relocate_keeps_record_and_active_project` asserts neither changes. `test_history_write_error_does_not_fail_project_save` asserts the JSON save succeeds and the status bar reports `历史记录更新失败`.
- [ ] **Step 5: Implement Relocate/Remove and safe history-error feedback.** Validate with `ProjectStore.load`; user-chosen paths may be outside the old directory, but automatic scan remains confined to the recorded directory.
- [ ] **Step 6: Run `python -m pytest -q`; `python -m black --check --diff ui services tests`; `python -m flake8 . --max-line-length=120 --extend-ignore=E501,E402,E203,F401,F541`; `python -m compileall -q ui services`.** Expect all to pass. Inspect `git diff --check` and a native Qt screenshot.
- [ ] **Step 7: Rebuild with `python -m PyInstaller --noconfirm --clean '安服报告生成工具.spec'` and smoke-test the EXE.** Report the exact output path. Stage only this feature's changes; leave unrelated dirty edits untouched.

## Handoff

After Task 3, review the full feature against the spec, especially the scan boundary and unsaved-change behavior. Do not merge or push to GitHub unless the user requests it.
