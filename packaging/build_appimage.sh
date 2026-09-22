#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
APPDIR="$ROOT_DIR/build/appimage/AnfuReportWorkbench.AppDir"
DIST_EXECUTABLE="$ROOT_DIR/dist/anfu-report-generator"
OUTPUT="$ROOT_DIR/dist/anfu-report-generator-x86_64.AppImage"
TOOL="$ROOT_DIR/build/appimage/appimagetool-x86_64.AppImage"
TOOL_URL="https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage"

if [[ ! -x "$DIST_EXECUTABLE" ]]; then
    echo "Missing Linux executable: $DIST_EXECUTABLE" >&2
    exit 1
fi

rm -rf "$APPDIR"
install -Dm755 "$DIST_EXECUTABLE" "$APPDIR/usr/bin/anfu-report-generator"
install -Dm755 "$ROOT_DIR/packaging/linux/AppRun" "$APPDIR/AppRun"
install -Dm644 "$ROOT_DIR/packaging/linux/anfu-report-generator.desktop" "$APPDIR/anfu-report-generator.desktop"
install -Dm644 "$ROOT_DIR/packaging/linux/anfu-report-generator.svg" "$APPDIR/anfu-report-generator.svg"
install -Dm644 "$ROOT_DIR/packaging/linux/anfu-report-generator.desktop" "$APPDIR/usr/share/applications/anfu-report-generator.desktop"
install -Dm644 "$ROOT_DIR/packaging/linux/anfu-report-generator.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/anfu-report-generator.svg"

mkdir -p "$(dirname -- "$TOOL")"
if [[ ! -f "$TOOL" ]]; then
    curl --fail --location --retry 3 --output "$TOOL" "$TOOL_URL"
fi
chmod +x "$TOOL"

ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" "$APPDIR" "$OUTPUT"
chmod +x "$OUTPUT"
