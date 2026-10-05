"""Runtime path and asset resolution utilities for development and frozen PyInstaller bundles."""

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Check if the application is running inside a frozen PyInstaller binary."""
    return bool(getattr(sys, "frozen", False))


def get_bundle_root() -> Path:
    """Return the application root directory depending on whether execution is frozen or live."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass is not None:
            return Path(str(meipass)).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_asset_path(relative_path: str | Path) -> Path:
    """Resolve an asset path relative to the package root or PyInstaller extraction directory.

    Args:
        relative_path: Asset path or filename relative to the package or asset directory
                       (e.g., "ui/assets/logo.svg" or "logo.svg").

    Returns:
        Absolute Path to the resolved asset file or directory.
    """
    rel = Path(relative_path)
    base_dir = get_bundle_root()

    if is_frozen():
        candidate = base_dir / rel
        if candidate.exists():
            return candidate

        pkg_candidate = base_dir / "hikvision_downloader" / rel
        if pkg_candidate.exists():
            return pkg_candidate

        ui_assets_candidate = base_dir / "ui" / "assets" / rel.name
        if ui_assets_candidate.exists():
            return ui_assets_candidate

        assets_candidate = base_dir / "assets" / rel.name
        if assets_candidate.exists():
            return assets_candidate

        return candidate

    # Development or installed package execution
    candidate = base_dir / rel
    if candidate.exists():
        return candidate

    ui_assets_candidate = base_dir / "ui" / "assets" / rel
    if ui_assets_candidate.exists():
        return ui_assets_candidate

    ui_assets_name_candidate = base_dir / "ui" / "assets" / rel.name
    if ui_assets_name_candidate.exists():
        return ui_assets_name_candidate

    return candidate
