# PySide6 GUI Migration Design

## Goal

Replace the Tkinter interface with a professional PySide6 desktop interface while preserving the current project data, vulnerability library, report output, and image-paste behavior.

The selected visual direction is the light "professional workstation" style. The vulnerability workspace uses a left-hand findings list and a right-hand editor. The vulnerability library is a separate page and is also available through a searchable picker dialog.

## Scope

The first release changes only the GUI layer and the code boundaries needed to support it.

Included:

- PySide6 main window and styling.
- Findings page, vulnerability library page, picker dialog, batch-entry dialog, and library editor dialog.
- Project open/save and report-generation commands connected to the existing data and report code.
- Word/WPS text-and-image paste, image preview, and original-image preservation.
- Unsaved-change checks, error messages, status feedback, logging, and Windows packaging.
- Automated tests for extracted non-visual behavior and critical GUI flows.

Not included:

- Project dashboard or recent-project list.
- Automatic save or backup history.
- Report-template and style settings.
- Database, accounts, collaboration, or CLI expansion.

## Application Structure

`gui_app.py` remains the public GUI entry point but starts the PySide6 application. The new GUI is divided into focused modules:

- `ui/main_window.py`: application shell, project actions, sidebar navigation, page switching, and close handling.
- `ui/pages/findings_page.py`: findings list, search, ordering actions, and editor coordination.
- `ui/pages/library_page.py`: vulnerability template listing and CRUD actions.
- `ui/dialogs/library_picker.py`: searchable template picker used from the findings page.
- `ui/dialogs/batch_add_dialog.py`: current batch-entry behavior.
- `ui/widgets/finding_editor.py`: scrollable grouped finding form.
- `ui/widgets/evidence_editor.py`: rich text, image paste, preview, and screenshot-marker conversion.
- `services/project_store.py`: compatible JSON load/save and portable attachment handling.
- `services/clipboard_service.py`: clipboard decoding and normalized text/image segments.
- `services/report_service.py`: validation and calls into the existing `ReportBuilder`.

`report_builder.py` and `vuln_manager.py` keep their current public behavior. `report_generator.py` remains available but receives no new GUI-related features.

A small `ProjectState` object owns the project name, finding dictionaries, current project path, selected finding, and dirty state. It does not introduce a database or a general state framework.

## Main Window

The top bar contains the editable project name and the global actions: New, Open, Save, and Generate Report.

The sidebar contains two destinations:

- Findings
- Vulnerability Library

The page area uses `QStackedWidget`. The Findings page uses `QSplitter`, allowing the user to resize the findings list and editor while retaining sensible minimum widths.

The interface uses a restrained light palette, clear spacing, one blue accent color, low-contrast borders, and no decorative gradients or oversized cards.

## Findings Page

The left side contains:

- Search by vulnerability name, address, or network zone.
- New Finding, Add from Library, and Batch Entry actions.
- A compact list showing name, risk level, primary address, and network zone.
- Move up, move down, copy, and delete actions.

The right side contains a vertically scrollable form grouped into:

- Basic information: name, address, network zone, risk level, and remediation priority.
- Vulnerability content: description.
- Verification evidence: verification steps with images and verification result.
- Remediation: fix suggestion and remediation verification method.

Multiline fields retain their own vertical scrollbars. The editor action bar remains visible at the bottom and contains Clear Form and Save Finding.

If the user switches findings, changes pages, opens another project, or closes the application with unsaved editor changes, the application offers Save, Discard, and Cancel.

## Vulnerability Library

The library is no longer permanently visible beside the editor.

The library page supports search, category filtering, preview, add, edit, and delete. Library changes continue to use the existing JSON file and `VulnManager` behavior.

The Add from Library dialog displays search and filters on the left and a full template preview on the right. Adding a template creates a project finding, closes the dialog, selects the new finding, and leaves the address and evidence ready for completion.

## Clipboard and Images

`EvidenceEditor` subclasses `QTextEdit` and accepts rich clipboard content. Clipboard handling follows this order:

1. Read Qt MIME image, HTML, and text data.
2. Preserve text-and-image order where the source provides it.
3. Use the existing Windows clipboard decoding path as a fallback for Word/WPS formats such as DIB and enhanced metafiles.
4. Reject blank image candidates and retain the highest-quality valid candidate.
5. Flatten transparency onto white before saving PNG files.

Original images are written to disk immediately. The editor displays scaled previews and releases preview resources when content is removed or a project is replaced. Project data continues to represent evidence images with `[截图: path]` markers, preserving compatibility with existing projects and `ReportBuilder`.

Report generation always uses the saved original image, never the preview, so reducing preview memory does not reduce report quality.

## Data Flow and Compatibility

Opening a project:

1. `ProjectStore` reads the existing JSON shape.
2. Relative attachment paths are resolved against the project directory.
3. `ProjectState` is populated and the pages refresh from it.

Saving a project:

1. The active form is validated and committed to `ProjectState`.
2. Attachments are copied to the existing `<project>_attachments` directory convention.
3. Screenshot paths are written as portable relative paths.
4. JSON retains the existing `project_name` and `findings` structure.

Generating a report:

1. The active form is committed.
2. Required data and missing images are checked.
3. The current finding dictionaries are passed to the existing `ReportBuilder` API.

Old project files and vulnerability-library files must open without migration. Files saved by the PySide6 version must remain readable by the previous data layer.

## Errors and Feedback

Destructive actions and unsaved changes use confirmation dialogs. Ordinary successful actions use the status bar instead of modal success dialogs.

Project, clipboard, attachment, and report failures show a short actionable message. Technical details are written to a rotating local log. Missing evidence images are visibly marked in the editor and summarized before report generation rather than silently ignored.

An operation that fails must not clear the current form or replace the current project state.

## Testing and Acceptance

Automated tests cover:

- Existing and newly saved project JSON compatibility.
- Relative attachment copying and path resolution.
- Clipboard candidate selection, blank-image rejection, transparency flattening, and marker ordering.
- Vulnerability library CRUD and template-to-finding conversion.
- Report-service validation and calls to `ReportBuilder`.
- GUI smoke flows with `pytest-qt`: start, navigate, edit, save, reload, and guard unsaved changes.

Manual Windows acceptance covers:

- Create, edit, copy, order, delete, and batch-add findings.
- Open and save an existing project and vulnerability library.
- Paste mixed text and images from Microsoft Word and WPS without blank images or reordered content.
- Paste a single screenshot and multiple images.
- Generate a report with the same field content and ordering as the current version.
- Confirm that report images retain original quality.
- Repeatedly paste and remove large images and confirm preview memory is released.
- Build and launch the packaged application on a Windows machine without Python installed.

The old Tkinter GUI remains available only during migration for behavior comparison. After all acceptance checks pass, `gui_app.py` launches only the PySide6 GUI and obsolete Tkinter UI code is removed.

## Later Backlog

- Project home and recent projects.
- Automatic save and simple backups.
- Report template and style settings.
