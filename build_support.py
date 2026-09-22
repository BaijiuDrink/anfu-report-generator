from pathlib import PureWindowsPath
import sys

SYSTEM_DLL_COLLISIONS = {"icuuc.dll", "icudt78.dll"}


def executable_name(platform_name=None):
    platform_name = platform_name or sys.platform
    if platform_name == "win32":
        return "安服报告生成工具"
    return "anfu-report-generator"


def remove_colliding_system_dlls(binaries):
    """Drop third-party DLLs that shadow compatible Windows system DLLs."""
    return [
        entry
        for entry in binaries
        if PureWindowsPath(entry[0]).name.casefold() not in SYSTEM_DLL_COLLISIONS
    ]
