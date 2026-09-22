from pathlib import PureWindowsPath

SYSTEM_DLL_COLLISIONS = {"icuuc.dll", "icudt78.dll"}


def remove_colliding_system_dlls(binaries):
    """Drop third-party DLLs that shadow compatible Windows system DLLs."""
    return [
        entry
        for entry in binaries
        if PureWindowsPath(entry[0]).name.casefold() not in SYSTEM_DLL_COLLISIONS
    ]
