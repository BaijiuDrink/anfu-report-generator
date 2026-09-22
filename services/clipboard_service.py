from __future__ import annotations

import base64
import ctypes
import datetime
import html as html_module
import io
import logging
import os
import re
import struct
from pathlib import Path
from urllib.parse import unquote

from PIL import Image, ImageGrab
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication

try:
    import win32clipboard
except ImportError:  # pragma: no cover - only relevant off Windows
    win32clipboard = None

ClipboardSegment = str | Image.Image
LOGGER = logging.getLogger(__name__)


def copy_image(image: Image.Image) -> Image.Image:
    image.load()
    return image.copy()


def flatten_transparency(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.copy()


def image_quality_score(image: Image.Image) -> int:
    return image.width * image.height


def image_has_visible_content(image: Image.Image) -> bool:
    preview = flatten_transparency(image).convert("RGB")
    preview.thumbnail((64, 64), Image.Resampling.LANCZOS)
    extrema = preview.getextrema()
    if any(high - low > 2 for low, high in extrema):
        return True
    sample = preview.getpixel((0, 0))
    return not all(channel >= 253 for channel in sample) and not all(
        channel <= 2 for channel in sample
    )


def image_signature(image: Image.Image) -> tuple[tuple[int, int], int]:
    thumbnail = flatten_transparency(image).convert("RGB")
    thumbnail.thumbnail((32, 32), Image.Resampling.LANCZOS)
    return image.size, hash(thumbnail.tobytes())


def prefer_best_images(
    segments: list[ClipboardSegment], candidates: list[Image.Image]
) -> list[ClipboardSegment]:
    result = list(segments)
    image_indexes = [
        index for index, item in enumerate(result) if isinstance(item, Image.Image)
    ]
    visible = [item for item in candidates if image_has_visible_content(item)]
    if not image_indexes or not visible:
        return result

    unique: dict[tuple[tuple[int, int], int], Image.Image] = {}
    for candidate in visible:
        signature = image_signature(candidate)
        current = unique.get(signature)
        if current is None or image_quality_score(candidate) > image_quality_score(
            current
        ):
            unique[signature] = candidate
    available = list(unique.values())

    if len(image_indexes) == 1:
        available = [max(available, key=image_quality_score)]
    elif len(available) != len(image_indexes):
        return result

    for index in image_indexes:
        current = result[index]
        current_ratio = current.width / max(current.height, 1)
        best = min(
            available,
            key=lambda image: abs(image.width / max(image.height, 1) - current_ratio),
        )
        ratio_diff = abs(best.width / max(best.height, 1) - current_ratio) / max(
            current_ratio, 0.0001
        )
        if ratio_diff <= 0.02 and image_quality_score(best) > image_quality_score(
            current
        ):
            result[index] = best
        available.remove(best)
    return result


def _decode_encoded_image(data: bytes) -> Image.Image | None:
    try:
        with Image.open(io.BytesIO(data)) as image:
            return copy_image(image)
    except Exception:
        LOGGER.debug("Unable to decode encoded clipboard image", exc_info=True)
        return None


def _image_from_src(src: str) -> Image.Image | None:
    try:
        if src.lower().startswith("data:image"):
            encoded = re.search(r"base64,([^\s]+)", src, re.IGNORECASE)
            if encoded:
                return _decode_encoded_image(base64.b64decode(encoded.group(1)))
        if src.lower().startswith("file:"):
            raw_path = src
            for prefix in ("file:///", "file://", "file:"):
                if raw_path.lower().startswith(prefix):
                    raw_path = raw_path[len(prefix) :]
                    break
            raw_path = unquote(raw_path).replace("/", os.sep)
            if os.path.exists(raw_path):
                with Image.open(raw_path) as image:
                    return copy_image(image)
    except Exception:
        LOGGER.debug("Unable to decode HTML clipboard image", exc_info=True)
    return None


def parse_html_clipboard(html_data: bytes | str) -> list[ClipboardSegment]:
    if isinstance(html_data, str):
        html_bytes = html_data.encode("utf-8")
    else:
        html_bytes = html_data

    try:
        header = html_bytes[: min(len(html_bytes), 4096)]
        start_match = re.search(rb"StartFragment:(\d+)", header)
        end_match = re.search(rb"EndFragment:(\d+)", header)
        fragment = html_bytes
        if start_match and end_match:
            start = int(start_match.group(1))
            end = int(end_match.group(1))
            if 0 <= start < end <= len(html_bytes):
                fragment = html_bytes[start:end]
        else:
            marker_start = html_bytes.find(b"<!--StartFragment-->")
            marker_end = html_bytes.find(b"<!--EndFragment-->")
            if marker_start >= 0 and marker_end > marker_start:
                marker_start += len(b"<!--StartFragment-->")
                fragment = html_bytes[marker_start:marker_end]
        fragment_text = fragment.decode("utf-8", errors="ignore")
    except Exception:
        LOGGER.debug("Unable to parse HTML clipboard header", exc_info=True)
        return []

    segments: list[ClipboardSegment] = []
    image_tag = re.compile(r"(<img[^>]*>)", re.IGNORECASE)
    image_src = re.compile(r'src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    for part in image_tag.split(fragment_text):
        if not part:
            continue
        if part.lower().startswith("<img"):
            source = image_src.search(part)
            image = _image_from_src(source.group(1)) if source else None
            if image is not None:
                segments.append(image)
            continue

        cleaned = re.sub(
            r"<style[^>]*>.*?</style>",
            "",
            part,
            flags=re.DOTALL | re.IGNORECASE,
        )
        cleaned = re.sub(
            r"<script[^>]*>.*?</script>",
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
        cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        cleaned = html_module.unescape(cleaned)
        cleaned = re.sub(r"[{}@]", "", cleaned)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n\s*\n+", "\n", cleaned).strip()
        if cleaned:
            segments.append(cleaned)
    return segments


def _qimage_to_pillow(value) -> Image.Image | None:
    if isinstance(value, QPixmap):
        value = value.toImage()
    if not isinstance(value, QImage):
        return None
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    try:
        if not value.save(buffer, "PNG"):
            return None
        return _decode_encoded_image(bytes(buffer.data()))
    finally:
        buffer.close()


class ClipboardService:
    def read_segments(self, mime_data=None) -> list[ClipboardSegment]:
        if mime_data is None:
            app = QApplication.instance()
            mime_data = app.clipboard().mimeData() if app else None
        segments = self._read_qt_mime(mime_data)
        windows_candidates = self._read_windows_formats()
        if segments:
            return prefer_best_images(segments, windows_candidates)
        return self._best_visible_candidate(windows_candidates)

    def save_original_image(self, image: Image.Image, directory: Path) -> Path:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        filename = datetime.datetime.now().strftime("paste_%Y%m%d_%H%M%S_%f.png")
        path = directory / filename
        flatten_transparency(image).save(path, "PNG")
        return path

    def _read_qt_mime(self, mime_data) -> list[ClipboardSegment]:
        if mime_data is None:
            return []
        try:
            html_segments = []
            if mime_data.hasHtml():
                html_segments = parse_html_clipboard(mime_data.html())
                if any(isinstance(segment, Image.Image) for segment in html_segments):
                    return html_segments
            if mime_data.hasImage():
                image = _qimage_to_pillow(mime_data.imageData())
                return [image] if image is not None else []
            if html_segments:
                return html_segments
            if mime_data.hasText():
                text = mime_data.text()
                return [text] if text else []
        except Exception:
            LOGGER.exception("Unable to decode Qt clipboard content")
        return []

    @staticmethod
    def _best_visible_candidate(
        candidates: list[Image.Image],
    ) -> list[ClipboardSegment]:
        visible = [item for item in candidates if image_has_visible_content(item)]
        return [max(visible, key=image_quality_score)] if visible else []

    def _read_windows_formats(self) -> list[Image.Image]:
        candidates: list[Image.Image] = []
        try:
            grabbed = ImageGrab.grabclipboard()
            if isinstance(grabbed, Image.Image):
                candidates.append(copy_image(grabbed))
            elif isinstance(grabbed, list):
                for path in grabbed:
                    try:
                        with Image.open(path) as image:
                            candidates.append(copy_image(image))
                    except Exception:
                        LOGGER.debug(
                            "Unable to open clipboard file %s", path, exc_info=True
                        )
        except Exception:
            LOGGER.debug("Pillow clipboard fallback failed", exc_info=True)

        if win32clipboard is None:
            return candidates

        opened = False
        try:
            win32clipboard.OpenClipboard()
            opened = True
            html_format = win32clipboard.RegisterClipboardFormat("HTML Format")
            current = 0
            while True:
                current = win32clipboard.EnumClipboardFormats(current)
                if current == 0:
                    break
                if current == html_format:
                    data = win32clipboard.GetClipboardData(current)
                    for segment in parse_html_clipboard(data):
                        if isinstance(segment, Image.Image):
                            candidates.append(segment)
                    continue
                if current == 14:
                    image = self._emf_to_image(win32clipboard.GetClipboardData(current))
                    if image is not None:
                        candidates.append(image)
                    continue
                try:
                    format_name = win32clipboard.GetClipboardFormatName(current).lower()
                except Exception:
                    format_name = ""
                if format_name in ("png", "image/png"):
                    image = _decode_encoded_image(
                        win32clipboard.GetClipboardData(current)
                    )
                    if image is not None:
                        candidates.append(image)
                elif current in (8, 17):
                    image = self._decode_dib_image(
                        win32clipboard.GetClipboardData(current)
                    )
                    if image is not None:
                        candidates.append(image)
        except Exception:
            LOGGER.debug("Windows clipboard fallback failed", exc_info=True)
        finally:
            if opened:
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    LOGGER.debug("Unable to close Windows clipboard", exc_info=True)
        return candidates

    @staticmethod
    def _decode_dib_image(data: bytes) -> Image.Image | None:
        if not data or len(data) < 20:
            return None
        try:
            dib_size = struct.unpack_from("<I", data, 0)[0]
            if dib_size < 12 or dib_size > len(data):
                return None
            if dib_size >= 40:
                bit_count = struct.unpack_from("<H", data, 14)[0]
                compression = struct.unpack_from("<I", data, 16)[0]
                colors_used = struct.unpack_from("<I", data, 32)[0]
                palette_entries = colors_used or (
                    1 << bit_count if bit_count <= 8 else 0
                )
                masks_size = 12 if dib_size == 40 and compression in (3, 6) else 0
                pixel_offset = 14 + dib_size + masks_size + palette_entries * 4
            else:
                bit_count = struct.unpack_from("<H", data, 10)[0]
                palette_entries = 1 << bit_count if bit_count <= 8 else 0
                pixel_offset = 14 + dib_size + palette_entries * 3
            header = struct.pack("<2sIHHI", b"BM", 14 + len(data), 0, 0, pixel_offset)
            return _decode_encoded_image(header + data)
        except Exception:
            LOGGER.debug("Unable to decode DIB clipboard image", exc_info=True)
            return None

    @staticmethod
    def _emf_to_image(emf_data: bytes) -> Image.Image | None:
        if not emf_data or len(emf_data) < 52:
            return None
        try:
            gdi32 = ctypes.windll.gdi32
            left, top, right, bottom = struct.unpack_from("<iiii", emf_data, 24)
            native_width = max(int(max(right - left, 1) * 300 / 2540), 1)
            native_height = max(int(max(bottom - top, 1) * 300 / 2540), 1)
            scale = min(6000 / native_width, 6000 / native_height, 1)
            width = max(int(native_width * scale), 1)
            height = max(int(native_height * scale), 1)
            hdc = gdi32.CreateDCW("DISPLAY", None, None, None)
            if not hdc:
                return None
            try:
                mdc = gdi32.CreateCompatibleDC(hdc)
                if not mdc:
                    return None
                try:

                    class BitmapInfo(ctypes.Structure):
                        _fields_ = [
                            ("biSize", ctypes.c_uint32),
                            ("biWidth", ctypes.c_int32),
                            ("biHeight", ctypes.c_int32),
                            ("biPlanes", ctypes.c_uint16),
                            ("biBitCount", ctypes.c_uint16),
                            ("biCompression", ctypes.c_uint32),
                            ("biSizeImage", ctypes.c_uint32),
                            ("biXPelsPerMeter", ctypes.c_int32),
                            ("biYPelsPerMeter", ctypes.c_int32),
                            ("biClrUsed", ctypes.c_uint32),
                            ("biClrImportant", ctypes.c_uint32),
                        ]

                    info = BitmapInfo()
                    info.biSize = ctypes.sizeof(BitmapInfo)
                    info.biWidth = width
                    info.biHeight = -height
                    info.biPlanes = 1
                    info.biBitCount = 32
                    bits = ctypes.c_void_p()
                    bitmap = gdi32.CreateDIBSection(
                        mdc, ctypes.byref(info), 0, ctypes.byref(bits), None, 0
                    )
                    if not bitmap:
                        return None
                    try:
                        old_bitmap = gdi32.SelectObject(mdc, bitmap)
                        gdi32.PatBlt(mdc, 0, 0, width, height, 0x00FF0062)
                        metafile = gdi32.SetEnhMetaFileBits(len(emf_data), emf_data)
                        rendered = False
                        if metafile:
                            from ctypes import wintypes

                            rect = wintypes.RECT(0, 0, width, height)
                            rendered = gdi32.PlayEnhMetaFile(
                                mdc, metafile, ctypes.byref(rect)
                            )
                            gdi32.DeleteEnhMetaFile(metafile)
                        gdi32.SelectObject(mdc, old_bitmap)
                        if not rendered:
                            return None
                        pixel_data = ctypes.string_at(bits, width * height * 4)
                        return Image.frombuffer(
                            "RGB",
                            (width, height),
                            pixel_data,
                            "raw",
                            "BGRX",
                            0,
                            1,
                        )
                    finally:
                        gdi32.DeleteObject(bitmap)
                finally:
                    gdi32.DeleteDC(mdc)
            finally:
                gdi32.DeleteDC(hdc)
        except Exception:
            LOGGER.debug("Unable to render enhanced metafile", exc_info=True)
            return None
