"""Unit tests for runtime asset path resolution under standard and frozen environments."""

import sys
from pathlib import Path

import pytest

from hikvision_downloader.paths import get_asset_path, get_bundle_root, is_frozen


def test_is_frozen_standard_execution() -> None:
    """Verify is_frozen returns False when sys.frozen is not set."""
    if hasattr(sys, "frozen"):
        delattr(sys, "frozen")
    assert is_frozen() is False


def test_is_frozen_when_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify is_frozen returns True when sys.frozen is set to True."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert is_frozen() is True


def test_get_bundle_root_standard_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify get_bundle_root returns package root in standard execution."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    root = get_bundle_root()
    assert isinstance(root, Path)
    assert (root / "paths.py").exists()


def test_get_bundle_root_frozen_with_meipass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify get_bundle_root returns sys._MEIPASS when frozen."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert get_bundle_root() == tmp_path.resolve()


def test_get_bundle_root_frozen_without_meipass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify get_bundle_root falls back to sys.executable directory when _MEIPASS is absent."""
    fake_exe = tmp_path / "app_binary"
    fake_exe.touch()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    assert get_bundle_root() == tmp_path.resolve()


def test_get_asset_path_standard_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify get_asset_path resolves standard repository assets."""
    monkeypatch.delattr(sys, "frozen", raising=False)

    logo_path = get_asset_path("ui/assets/logo.svg")
    assert logo_path.exists()
    assert logo_path.name == "logo.svg"

    favicon_path = get_asset_path("ui/assets/favicon.svg")
    assert favicon_path.exists()
    assert favicon_path.name == "favicon.svg"

    arivedha_logo_path = get_asset_path("ui/assets/arivedha_logo.svg")
    assert arivedha_logo_path.exists()
    assert arivedha_logo_path.name == "arivedha_logo.svg"

    # Shorthand resolution
    shorthand_path = get_asset_path("logo.svg")
    assert shorthand_path.exists()
    assert shorthand_path.name == "logo.svg"

    # Non-existent fallback
    fallback_path = get_asset_path("non_existent_asset.xyz")
    assert fallback_path.name == "non_existent_asset.xyz"


def test_get_asset_path_frozen_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify get_asset_path resolves assets correctly from PyInstaller extraction roots."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    # 1. Direct relative match in bundle root
    direct_asset = tmp_path / "ui" / "assets" / "direct.svg"
    direct_asset.parent.mkdir(parents=True, exist_ok=True)
    direct_asset.write_text("<svg>direct</svg>", encoding="utf-8")

    assert get_asset_path("ui/assets/direct.svg") == direct_asset

    # 2. Match under hikvision_downloader package directory
    pkg_asset = tmp_path / "hikvision_downloader" / "ui" / "assets" / "pkg.svg"
    pkg_asset.parent.mkdir(parents=True, exist_ok=True)
    pkg_asset.write_text("<svg>pkg</svg>", encoding="utf-8")

    assert get_asset_path("ui/assets/pkg.svg") == pkg_asset

    # 3. Match under ui/assets using basename
    ui_asset = tmp_path / "ui" / "assets" / "base_match.svg"
    ui_asset.write_text("<svg>base</svg>", encoding="utf-8")

    assert get_asset_path("base_match.svg") == ui_asset

    # 4. Match under assets root using basename
    assets_root = tmp_path / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)
    root_asset = assets_root / "root_match.svg"
    root_asset.write_text("<svg>root</svg>", encoding="utf-8")

    assert get_asset_path("root_match.svg") == root_asset

    # 5. Non-existent fallback
    fallback = get_asset_path("missing_icon.png")
    assert fallback == tmp_path / "missing_icon.png"
