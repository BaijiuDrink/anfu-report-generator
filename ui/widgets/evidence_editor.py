from __future__ import annotations

import re
import uuid
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage, QTextDocument, QTextImageFormat
from PySide6.QtWidgets import QTextEdit

from services.clipboard_service import ClipboardSegment, ClipboardService

SCREENSHOT_PATTERN = re.compile(r"\[截图:\s*(.*?)\]")


class EvidenceEditor(QTextEdit):
    def __init__(self, screenshot_dir, clipboard_service=None, parent=None):
        super().__init__(parent)
        self.screenshot_dir = Path(screenshot_dir)
        self.clipboard_service = clipboard_service or ClipboardService()
        self._image_paths: list[Path] = []
        self._preview_urls: set[str] = set()
        self._missing_paths: list[Path] = []
        self.setAcceptRichText(True)
        self.setPlaceholderText("输入验证步骤，可直接从 Word/WPS 粘贴图文内容")

    def insertFromMimeData(self, source):
        segments = self.clipboard_service.read_segments(source)
        if segments:
            self.paste_segments(segments)
            return
        super().insertFromMimeData(source)

    def paste_segments(self, segments: list[ClipboardSegment]) -> None:
        cursor = self.textCursor()
        for segment in segments:
            if isinstance(segment, str):
                cursor.insertText(segment)
                continue
            if isinstance(segment, Image.Image):
                path = self.clipboard_service.save_original_image(
                    segment, self.screenshot_dir
                )
                self._image_paths.append(path)
                self._insert_preview(cursor, path)
                cursor.insertText(f"\n[截图: {path}]\n")
        self.setTextCursor(cursor)

    def set_marker_text(self, content: str, base_dir: Path | None = None) -> None:
        self.clear()
        cursor = self.textCursor()
        position = 0
        for match in SCREENSHOT_PATTERN.finditer(content or ""):
            cursor.insertText(content[position : match.start()])
            raw_path = match.group(1)
            resolved = Path(raw_path)
            if not resolved.is_absolute() and base_dir is not None:
                resolved = Path(base_dir) / resolved
            if resolved.exists() and self._insert_preview(cursor, resolved):
                self._image_paths.append(resolved)
                cursor.insertText("\n")
            else:
                self._missing_paths.append(resolved)
            cursor.insertText(match.group(0))
            position = match.end()
        cursor.insertText((content or "")[position:])
        self.setTextCursor(cursor)

    def marker_text(self) -> str:
        return self.toPlainText().replace("\ufffc", "").strip()

    def image_paths(self) -> list[Path]:
        return list(self._image_paths)

    def missing_images(self) -> list[Path]:
        return list(self._missing_paths)

    def preview_resource_count(self) -> int:
        return len(self._preview_urls)

    def clear(self) -> None:
        self.setDocument(QTextDocument(self))
        self._image_paths.clear()
        self._preview_urls.clear()
        self._missing_paths.clear()

    def _insert_preview(self, cursor, path: Path) -> bool:
        image = QImage(str(path))
        if image.isNull():
            return False
        preview = image.scaled(
            1000,
            700,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        resource_url = QUrl(f"evidence-preview://{uuid.uuid4().hex}")
        self.document().addResource(QTextDocument.ImageResource, resource_url, preview)
        image_format = QTextImageFormat()
        image_format.setName(resource_url.toString())
        image_format.setWidth(preview.width())
        image_format.setHeight(preview.height())
        cursor.insertImage(image_format)
        self._preview_urls.add(resource_url.toString())
        return True
