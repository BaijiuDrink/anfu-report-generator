import base64
import io

from PIL import Image

from services import clipboard_service as clipboard_module
from services.clipboard_service import (
    ClipboardService,
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
    html = (
        "Start<!--StartFragment-->before"
        f"<img src='{png_data_uri((20, 10), (255, 0, 0, 255))}'>"
        "after<!--EndFragment-->"
    )
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


def test_word_fallback_replaces_blank_preview_with_high_resolution(monkeypatch):
    service = ClipboardService()
    blank = Image.new("RGBA", (100, 50), (255, 255, 255, 0))
    high = Image.new("RGB", (1600, 800), "blue")
    monkeypatch.setattr(service, "_read_qt_mime", lambda mime: [blank])
    monkeypatch.setattr(service, "_read_windows_formats", lambda: [high])

    segments = service.read_segments(object())

    assert segments[0].size == (1600, 800)


def test_mixed_html_and_image_prefers_ordered_html_segments(monkeypatch):
    service = ClipboardService()
    html = (
        "<!--StartFragment-->before"
        f"<img src='{png_data_uri((20, 10), (255, 0, 0, 255))}'>"
        "after<!--EndFragment-->"
    )

    class MixedMimeData:
        @staticmethod
        def hasImage():
            return True

        @staticmethod
        def imageData():
            return object()

        @staticmethod
        def hasHtml():
            return True

        @staticmethod
        def html():
            return html

        @staticmethod
        def hasText():
            return True

    monkeypatch.setattr(
        clipboard_module,
        "_qimage_to_pillow",
        lambda _value: Image.new("RGB", (100, 50), "blue"),
    )

    segments = service._read_qt_mime(MixedMimeData())

    assert segments[0] == "before"
    assert isinstance(segments[1], Image.Image)
    assert segments[2] == "after"


def test_windows_clipboard_is_closed_when_enumeration_raises(monkeypatch):
    events = []

    class BrokenClipboard:
        def OpenClipboard(self):
            events.append("open")

        def CloseClipboard(self):
            events.append("close")

        def RegisterClipboardFormat(self, name):
            return 100

        def EnumClipboardFormats(self, previous):
            raise RuntimeError("broken")

    monkeypatch.setattr(clipboard_module, "win32clipboard", BrokenClipboard())
    monkeypatch.setattr(clipboard_module.ImageGrab, "grabclipboard", lambda: None)

    assert ClipboardService()._read_windows_formats() == []
    assert events == ["open", "close"]
