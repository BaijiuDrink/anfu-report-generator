# -*- mode: python ; coding: utf-8 -*-

from build_support import remove_colliding_system_dlls


a = Analysis(
    ["gui_app.py"],
    pathex=[],
    binaries=[],
    datas=[("vuln_library/default_vulns.json", "vuln_library")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a.binaries = remove_colliding_system_dlls(a.binaries)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="安服报告生成工具",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
