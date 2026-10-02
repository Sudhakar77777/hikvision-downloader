import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values

pytestmark = pytest.mark.integration


def test_cli_help_subprocess() -> None:
    """Verify that 'python -m hikvision_downloader --help' executes cleanly in a fresh process with zero import errors."""
    project_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "-m", "hikvision_downloader", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"CLI help failed with stderr: {result.stderr}"
    assert "hikvision-downloader" in result.stdout
    assert "--date" in result.stdout
    assert "--camera" in result.stdout
    assert "--stream" in result.stdout
    assert "--range" in result.stdout
    assert "--non-interactive" in result.stdout
    assert "Ctrl+C" in result.stdout


def test_cli_version_subprocess() -> None:
    """Verify that 'python -m hikvision_downloader --version' outputs version string in a fresh process."""
    project_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "-m", "hikvision_downloader", "--version"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"CLI version failed with stderr: {result.stderr}"
    assert "hikvision-downloader 0.1.0" in result.stdout


def test_cli_entrypoint_script_subprocess() -> None:
    """Verify that the console script entry point executes without import errors."""
    project_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        ["uv", "run", "hikvision-downloader", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"Console script failed with stderr: {result.stderr}"
    assert "hikvision-downloader" in result.stdout
    assert "--non-interactive" in result.stdout


def test_cli_non_interactive_validation_subprocess() -> None:
    """Verify that running non-interactive mode with missing options cleanly fails with exit code 1."""
    project_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "-m", "hikvision_downloader", "--non-interactive"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "ERROR" in result.stdout or "ERROR" in result.stderr


def test_live_cli_execution_with_nvr(tmp_path: Path) -> None:
    """Verify live CLI execution against real NVR hardware if configured in .env."""
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"

    if not env_path.exists():
        pytest.skip("Integration test skipped: .env file does not exist")

    env_config = dotenv_values(env_path)
    host = env_config.get("HIKVISION_HOST") or os.getenv("HIKVISION_HOST")
    cookie = env_config.get("HIKVISION_COOKIE") or os.getenv("HIKVISION_COOKIE")

    if not host or not cookie:
        pytest.skip("Integration test skipped: HIKVISION_HOST or HIKVISION_COOKIE not configured")

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "hikvision_downloader",
                "--date",
                "2026-09-15",
                "--camera",
                "4",
                "--stream",
                "main",
                "--range",
                "1 1",
                "--output-dir",
                str(tmp_path),
                "--non-interactive",

            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=30.0,
        )
    except subprocess.TimeoutExpired:
        pytest.skip("Live NVR hardware unreachable: command timed out after 30.0s")

    # If NVR is unreachable on network, skip; otherwise verify valid CLI execution
    if result.returncode != 0 and ("Connection" in result.stderr or "timed out" in result.stderr or "SEARCH FAILED" in result.stderr):
        pytest.skip(f"Live NVR hardware unreachable: {result.stderr or result.stdout}")

    assert result.returncode == 0, f"Live CLI download failed with stderr: {result.stderr}\nstdout: {result.stdout}"
    assert "DOWNLOAD BATCH COMPLETE" in result.stdout
    # Verify downloaded CSV and MP4 exist
    csv_files = list(tmp_path.glob("*.csv"))
    mp4_files = list(tmp_path.glob("*.mp4"))
    assert len(csv_files) >= 1, "Expected recording list CSV in output directory"
    assert len(mp4_files) >= 1, "Expected downloaded video file in output directory"





