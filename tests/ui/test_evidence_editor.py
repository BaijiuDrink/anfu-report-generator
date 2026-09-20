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


def test_replacing_content_releases_previews_without_deleting_sources(qtbot, tmp_path):
    paths = []
    for index in range(5):
        path = tmp_path / f"proof-{index}.png"
        Image.new("RGB", (1200, 600), (index * 20, 20, 200)).save(path)
        paths.append(path)
    content = "\n".join(f"[截图: {path}]" for path in paths)
    editor = EvidenceEditor(tmp_path)
    qtbot.addWidget(editor)

    editor.set_marker_text(content)
    assert editor.preview_resource_count() == 5
    editor.set_marker_text("plain text")

    assert editor.preview_resource_count() == 0
    assert all(path.exists() for path in paths)
