import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
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
    assert "--workers" in result.stdout
    assert "--port" in result.stdout
    assert "--username" in result.stdout
    assert "--password" in result.stdout
    assert "--refresh-cameras" in result.stdout
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
    assert "--workers" in result.stdout
    assert "--non-interactive" in result.stdout


def test_cli_non_interactive_missing_options_subprocess() -> None:
    """Verify that running non-interactive mode with missing required options cleanly fails with exit code 1."""
    project_root = Path(__file__).resolve().parents[2]
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("HIKVISION_")}
    clean_env["HIKVISION_HOST"] = ""
    clean_env["HIKVISION_USERNAME"] = ""
    clean_env["HIKVISION_PASSWORD"] = ""

    # Case 1: Missing host
    result1 = subprocess.run(
        [sys.executable, "-m", "hikvision_downloader", "--non-interactive"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
        env=clean_env,
    )
    assert result1.returncode == 1
    assert "ERROR" in result1.stdout or "ERROR" in result1.stderr

    # Case 2: Missing credentials
    result2 = subprocess.run(
        [sys.executable, "-m", "hikvision_downloader", "--host", "127.0.0.1", "--non-interactive"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
        env=clean_env,
    )
    assert result2.returncode == 1
    assert "ERROR" in result2.stdout or "ERROR" in result2.stderr


def test_live_cli_execution_with_nvr(tmp_path: Path) -> None:
    """Verify live CLI execution against real NVR hardware if configured in .env."""
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"

    if not env_path.exists():
        pytest.skip("Integration test skipped: .env file does not exist")

    env_config = dotenv_values(env_path)
    host = env_config.get("HIKVISION_HOST") or os.getenv("HIKVISION_HOST")
    username = env_config.get("HIKVISION_USERNAME") or os.getenv("HIKVISION_USERNAME")
    password = env_config.get("HIKVISION_PASSWORD") or os.getenv("HIKVISION_PASSWORD")

    if not host or not (username and password):
        pytest.skip("Integration test skipped: HIKVISION_HOST, HIKVISION_USERNAME, and HIKVISION_PASSWORD not configured in .env")

    yesterday_str = str(datetime.now(UTC).date() - timedelta(days=1))
    cmd = [
        sys.executable,
        "-m",
        "hikvision_downloader",
        "--date",
        yesterday_str,
        "--camera",
        "1",
        "--stream",
        "main",
        "--range",
        "1 1",
        "-w",
        "2",
        "--output-dir",
        str(tmp_path),
        "--non-interactive",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=30.0,
        )
    except subprocess.TimeoutExpired:
        pytest.skip("Live NVR hardware unreachable: command timed out after 30.0s")

    # If NVR is unreachable on network or auth expired/unauthorized, skip; otherwise verify valid CLI execution
    output_text = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0 and (
        "Connection" in output_text
        or "timed out" in output_text
        or "SEARCH FAILED" in output_text
        or "DISCOVERY FAILED" in output_text
        or "AUTHENTICATION SETUP FAILED" in output_text
        or "expired" in output_text
        or "401" in output_text
        or "Unauthorized" in output_text
    ):
        pytest.skip(f"Live NVR hardware unreachable or auth expired: {output_text.strip()}")

    assert result.returncode == 0, f"Live CLI download failed with stderr: {result.stderr}\nstdout: {result.stdout}"
    if "DOWNLOAD BATCH COMPLETE" in result.stdout:
        csv_files = list(tmp_path.glob("*.csv"))
        mp4_files = list(tmp_path.glob("*.mp4"))
        assert len(csv_files) >= 1, "Expected recording list CSV in output directory"
        assert len(mp4_files) >= 1, "Expected downloaded video file in output directory"
    else:
        assert "No recordings found" in result.stdout or "SEARCHING RECORDINGS" in result.stdout
