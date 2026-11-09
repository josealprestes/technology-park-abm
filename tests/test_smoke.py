"""Smoke tests: every entry point runs end to end quickly.

These spawn real processes (module demo, experiment CLI, sensitivity CLI,
workbench server) and verify the minimal observable outcome.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.smoke


def test_module_cli_runs_and_is_deterministic() -> None:
    command = [sys.executable, "-m", "technology_park_abm"]
    first = subprocess.run(command, capture_output=True, text=True, check=False)
    second = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stdout.count("period") == 3
    assert first.stdout == second.stdout


def test_experiments_cli_smoke(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "technology_park_abm.experiments",
            "E5",
            "--seeds",
            "0",
            "--periods",
            "2",
            "--output",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0
    run_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "manifest.json").exists()
    assert (run_dirs[0] / "metrics.csv").exists()
    assert (run_dirs[0] / "summary.json").exists()


def test_sensitivity_cli_smoke(tmp_path: Path) -> None:
    output = tmp_path / "sensitivity.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "technology_park_abm.sensitivity",
            "--seeds",
            "0",
            "--periods",
            "2",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "baseline" in payload
    assert "variations" in payload


def test_cli_rejects_zero_periods() -> None:
    cases = (
        [sys.executable, "-m", "technology_park_abm.experiments", "E5"],
        [sys.executable, "-m", "technology_park_abm.sensitivity"],
    )
    for command in cases:
        result = subprocess.run(
            [*command, "--periods", "0"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 2
        assert "periods must be at least 1" in result.stderr


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.e2e
def test_workbench_server_subprocess_smoke(tmp_path: Path) -> None:
    build = subprocess.run(
        [sys.executable, "scripts/build_investigation_prototype.py"],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert build.returncode == 0
    port = _free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "scripts/serve_investigation_prototype.py",
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        health: dict[str, Any] | None = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(
                    f"{base}/api/investigation/health", timeout=2
                ) as response:
                    health = json.loads(response.read().decode("utf-8"))
                break
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                time.sleep(0.2)
        assert health is not None
        assert health["available"] is True
        build_info = health["build"]
        assert build_info["version"]
        assert build_info["git_commit"]
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
