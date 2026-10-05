#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "=== [1/4] Generating Application Icons ==="
uv run python packaging/generate_icons.py

echo "=== [2/4] Building macOS Application Bundle via PyInstaller ==="
uv run pyinstaller packaging/hikvision-downloader.spec --clean --noconfirm

echo "=== [3/4] Verifying and Ad-Hoc Signing .app Bundle ==="
APP_BUNDLE="dist/HikVision Downloader.app"
if [ ! -d "${APP_BUNDLE}" ]; then
    echo "Error: Application bundle '${APP_BUNDLE}' was not created." >&2
    exit 1
fi

echo "Signing application bundle with ad-hoc signature..."
codesign --force --deep -s - "${APP_BUNDLE}"

echo "=== [4/4] Creating Drag-and-Drop DMG Installer ==="
DMG_OUTPUT="dist/HikVision-Downloader-macOS.dmg"
rm -f "${DMG_OUTPUT}"

if command -v create-dmg >/dev/null 2>&1; then
    echo "Using create-dmg utility..."
    create-dmg \
        --volname "HikVision Downloader" \
        --volicon "packaging/assets/hikvision-downloader.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "HikVision Downloader.app" 175 160 \
        --hide-extension "HikVision Downloader.app" \
        --app-drop-link 425 160 \
        "${DMG_OUTPUT}" \
        "${APP_BUNDLE}" || {
            echo "create-dmg exited with non-zero status ($?), falling back to hdiutil..."
            rm -f "${DMG_OUTPUT}"
            USE_HDIUTIL=1
        }
else
    USE_HDIUTIL=1
fi

if [ "${USE_HDIUTIL:-0}" = "1" ]; then
    echo "Creating DMG with native macOS hdiutil..."
    STAGING_DIR="dist/dmg_staging"
    rm -rf "${STAGING_DIR}"
    mkdir -p "${STAGING_DIR}"

    cp -R "${APP_BUNDLE}" "${STAGING_DIR}/"
    ln -s /Applications "${STAGING_DIR}/Applications"

    hdiutil create \
        -volname "HikVision Downloader" \
        -srcfolder "${STAGING_DIR}" \
        -ov \
        -format UDZO \
        "${DMG_OUTPUT}"

    rm -rf "${STAGING_DIR}"
fi

echo "=== macOS Build Completed Successfully ==="
echo "Artifact: ${DMG_OUTPUT}"
ls -lh "${DMG_OUTPUT}"
