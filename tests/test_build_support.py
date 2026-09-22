from build_support import remove_colliding_system_dlls


def test_remove_colliding_system_dlls_keeps_unrelated_binaries():
    binaries = [
        ("icuuc.dll", r"C:\tools\poppler\icuuc.dll", "BINARY"),
        ("icudt78.dll", r"C:\tools\poppler\icudt78.dll", "BINARY"),
        ("PySide6\\Qt6Core.dll", r"C:\site-packages\PySide6\Qt6Core.dll", "BINARY"),
    ]

    assert remove_colliding_system_dlls(binaries) == [binaries[2]]
