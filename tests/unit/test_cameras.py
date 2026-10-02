from pathlib import Path

import pytest

from hikvision_downloader.core.cameras import load_cameras
from hikvision_downloader.core.models import CameraNumber, TrackId


def test_load_cameras_valid(tmp_path: Path) -> None:
    config_content = """
[[cameras]]
number = 1
name = "MainGate"
ip_address = "192.168.1.100"
main_track = 101
sub_track = 102

[[cameras]]
number = 2
name = "BackYard"
ip_address = "192.168.1.101"
main_track = 201
sub_track = 202
"""
    config_file = tmp_path / "cameras.toml"
    config_file.write_text(config_content, encoding="utf-8")

    cameras = load_cameras(config_file)
    assert len(cameras) == 2
    assert CameraNumber(1) in cameras
    assert CameraNumber(2) in cameras
    assert cameras[CameraNumber(1)].name == "MainGate"
    assert cameras[CameraNumber(1)].main_track == TrackId(101)
    assert cameras[CameraNumber(2)].name == "BackYard"
    assert cameras[CameraNumber(2)].sub_track == TrackId(202)


def test_load_cameras_missing_file(tmp_path: Path) -> None:
    non_existent = tmp_path / "missing.toml"
    with pytest.raises(FileNotFoundError, match="Camera configuration file not found"):
        load_cameras(non_existent)


def test_load_cameras_duplicate_number(tmp_path: Path) -> None:
    config_content = """
[[cameras]]
number = 1
name = "Cam1"
ip_address = "192.168.1.100"
main_track = 101
sub_track = 102

[[cameras]]
number = 1
name = "Cam1Duplicate"
ip_address = "192.168.1.101"
main_track = 201
sub_track = 202
"""
    config_file = tmp_path / "cameras.toml"
    config_file.write_text(config_content, encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate camera number '1'"):
        load_cameras(config_file)


def test_load_cameras_duplicate_main_track(tmp_path: Path) -> None:
    config_content = """
[[cameras]]
number = 1
name = "Cam1"
ip_address = "192.168.1.100"
main_track = 101
sub_track = 102

[[cameras]]
number = 2
name = "Cam2"
ip_address = "192.168.1.101"
main_track = 101
sub_track = 202
"""
    config_file = tmp_path / "cameras.toml"
    config_file.write_text(config_content, encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate main track ID '101'"):
        load_cameras(config_file)


def test_load_cameras_duplicate_sub_track(tmp_path: Path) -> None:
    config_content = """
[[cameras]]
number = 1
name = "Cam1"
ip_address = "192.168.1.100"
main_track = 101
sub_track = 102

[[cameras]]
number = 2
name = "Cam2"
ip_address = "192.168.1.101"
main_track = 201
sub_track = 102
"""
    config_file = tmp_path / "cameras.toml"
    config_file.write_text(config_content, encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate sub track ID '102'"):
        load_cameras(config_file)


def test_load_cameras_missing_cameras_key(tmp_path: Path) -> None:
    config_content = """
[other_section]
setting = true
"""
    config_file = tmp_path / "cameras.toml"
    config_file.write_text(config_content, encoding="utf-8")

    with pytest.raises(ValueError, match="No valid \\[\\[cameras\\]\\] definitions found"):
        load_cameras(config_file)


def test_load_cameras_empty_cameras_list(tmp_path: Path) -> None:
    config_content = """
cameras = []
"""
    config_file = tmp_path / "cameras.toml"
    config_file.write_text(config_content, encoding="utf-8")

    with pytest.raises(ValueError, match="No valid \\[\\[cameras\\]\\] definitions found"):
        load_cameras(config_file)
