# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for HikVision Downloader standalone desktop application."""

import os
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import PySide6

# Determine repository root
spec_dir = Path(SPECPATH).resolve()
repo_root = spec_dir.parent
src_dir = repo_root / "src"
ui_assets_dir = src_dir / "hikvision_downloader" / "ui" / "assets"
packaging_assets_dir = spec_dir / "assets"

# Bundled data assets
datas = [
    (str(ui_assets_dir), "hikvision_downloader/ui/assets"),
    (str(ui_assets_dir), "ui/assets"),
    (str(ui_assets_dir), "assets"),
]

# Ensure packaging icon assets are included if present
if packaging_assets_dir.exists():
    datas.append((str(packaging_assets_dir), "packaging/assets"))

# Explicitly collect PySide6 dynamic plugins (platforms, iconengines, imageformats, styles, etc.)
pyside6_dir = Path(PySide6.__file__).resolve().parent

# Check both standard plugins and Qt/plugins layouts
for plugin_type in ["platforms", "iconengines", "imageformats", "styles", "platformthemes", "tls"]:
    direct_plugin = pyside6_dir / "plugins" / plugin_type
    if direct_plugin.exists():
        datas.append((str(direct_plugin), f"PySide6/plugins/{plugin_type}"))
    qt_plugin = pyside6_dir / "Qt" / "plugins" / plugin_type
    if qt_plugin.exists():
        datas.append((str(qt_plugin), f"PySide6/Qt/plugins/{plugin_type}"))

# Hidden imports for reflection, platform keyrings, and dynamic backends
hiddenimports = [
    "keyring.backends",
    "keyring.backends.macOS",
    "keyring.backends.Windows",
    "keyring.backends.SecretService",
    "keyring.backends.null",
    "pydantic",
    "pydantic_core",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtNetwork",
]

hiddenimports += collect_submodules("keyring.backends")
hiddenimports += collect_submodules("pydantic")

# Target entry script
entry_script = str(spec_dir / "run_app.py")

# Icon path depending on platform
mac_icon = str(packaging_assets_dir / "hikvision-downloader.icns") if (packaging_assets_dir / "hikvision-downloader.icns").exists() else None
win_icon = str(packaging_assets_dir / "hikvision-downloader.ico") if (packaging_assets_dir / "hikvision-downloader.ico").exists() else None
app_icon = mac_icon if sys.platform == "darwin" else win_icon

block_cipher = None

a = Analysis(
    [entry_script],
    pathex=[str(src_dir), str(repo_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "numpy", "pandas", "mypy", "pytest", "ruff", "_pytest", "pluggy", "types_requests"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == "win32":
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="HikVision-Downloader-Windows-x64",
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
        icon=app_icon,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="hikvision-downloader",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=app_icon,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="hikvision-downloader",
    )

    app = BUNDLE(
        coll,
        name="HikVision Downloader.app",
        icon=mac_icon,
        bundle_identifier="com.arivedha.hikvision-downloader",
        info_plist={
            "CFBundleName": "HikVision Downloader",
            "CFBundleDisplayName": "HikVision Downloader",
            "CFBundleGetInfoString": "HikVision CCTV Video Archiving & Downloader",
            "CFBundleIdentifier": "com.arivedha.hikvision-downloader",
            "CFBundleVersion": "0.1.2",
            "CFBundleShortVersionString": "0.1.2",
            "NSHumanReadableCopyright": "Copyright © 2026 Arivedha. All rights reserved.",
            "NSHighResolutionCapable": "True",
            "LSApplicationCategoryType": "public.app-category.utilities",
        },
    )
