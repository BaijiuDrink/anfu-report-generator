# Project Management and Recent Projects Design

## Goal

Add a "项目管理" destination to the existing PySide6 workbench. It lists projects the user has successfully opened or saved and opens each one from its JSON file. Keep the current light three-column visual language and the existing unsaved-change protection.

The user chose a strict recovery boundary: automatically scan only the directory that held each recorded JSON file. Never scan other folders, configured roots, or whole disks. A file moved outside that directory is marked "JSON 文件已移动" until the user manually locates it.

## Selected Approach

Keep a small application-local recent-project index separate from project JSON files. Each record stores the last known absolute path, original directory, display name, last-opened time, and SHA-256 digest of the JSON bytes. The digest identifies a renamed file in the same directory without changing existing project files. Opening or saving a project updates its record and digest.

Alternatives considered:

- Paths only: simpler, but cannot recognize a same-directory rename.
- A new ID inside every project JSON: stronger identity, but changes the shared file format and requires migration of old projects.

The index-plus-digest approach preserves existing JSON compatibility. If a moved file was also edited, its digest may no longer match; the user can relink it manually.

## Components and Data Flow

- `services/project_history.py` owns the index, its persistence, registration of successful opens/saves, and same-directory recovery. The default index path comes from Qt's local application-data location; tests can inject a temporary path. Writes are atomic so a partial write does not destroy history.
- `ui/pages/projects_page.py` displays recent projects in a searchable list with name, last known path, last-opened time, and status. It provides Open, Relocate, and Remove from History actions. Removing a record never deletes its JSON file.
- `ui/main_window.py` adds the sidebar destination, wires actions, and records only successful project open/save operations. Opening a history item goes through the existing `open_project` path, including unsaved-change checks and normal JSON/attachment loading.
- `ui/theme.py` applies the current light palette, restrained cards, spacing, and status colors to the new page.

Entering Project Management refreshes every record. For a missing path, the service scans only its recorded parent directory, non-recursively, for `*.json`. If exactly one candidate has the stored digest, it updates the path. With no match, an unavailable directory, or multiple matches, it does not guess and shows "JSON 文件已移动". Opening a missing item performs the same check again before presenting the state.

Manual Relocate opens a file picker initiated by the user; it may select a JSON file anywhere. The selected file must load as a project. If its project name differs from the historical record, the UI asks for confirmation before replacing the association. After a successful relink, that file's parent becomes the record's new original directory.

## UX and Failure Handling

The sidebar shows "项目管理" beside "漏洞管理" and "漏洞库". The page has a title and count, search field, and compact project cards consistent with the findings list. Missing records show "JSON 文件已移动" directly after the project name and offer "重新定位". A tooltip can note that deletion is also possible. A newly opened or saved project appears immediately in the list.

An invalid or unreadable project JSON is reported as an open error and is not registered as a new successful project. Failure to write the history index does not prevent opening or saving the project; the UI reports that recent-project history could not be updated and logs the error. If the index is corrupt, preserve a copy before rebuilding an empty index. No automatic scan leaves a recorded original directory.

## Tests

- Service tests cover registration, persistence, same-directory rename recovery, no scan outside the original directory, ambiguous digest matches, and damaged-index handling.
- UI tests cover navigation, list status, Open/Relocate/Remove actions, and preservation of unsaved-change decisions.
- Run the full pytest suite, formatting/lint/compile checks, render a native Qt preview, and rebuild/smoke-test the Windows EXE.

## Out of Scope

No full-disk discovery, recursive search, filesystem watching, account sync, automatic backups, or changes to report generation or the project JSON schema.
