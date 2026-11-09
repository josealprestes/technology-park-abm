"""Run manifest construction per docs/adr/0003.

The experiment runner (F4) adds run identifiers and output paths; this module
centralizes version capture and configuration embedding.
"""

from __future__ import annotations

import importlib.metadata
import platform
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from .config import ModelConfig
from .metrics import METRIC_SCHEMA_VERSION

MANIFEST_SCHEMA_VERSION = "1.0"


def package_version() -> str:
    """Return the installed package version, or "unknown" when unavailable."""
    try:
        return importlib.metadata.version("technology-park-abm")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def mesa_version() -> str:
    """Return the installed Mesa version, or "unknown" when unavailable."""
    try:
        return importlib.metadata.version("mesa")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _git(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_commit() -> str | None:
    """Return the current commit hash, or None when unavailable."""
    commit = _git(["rev-parse", "HEAD"])
    return commit or None


def git_dirty() -> bool | None:
    """Return whether the working tree has uncommitted changes, or None."""
    status = _git(["status", "--porcelain"])
    if status is None:
        return None
    return bool(status)


def build_manifest(config: ModelConfig) -> dict[str, Any]:
    """Build a manifest capturing configuration, versions, and schema."""
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "created_utc": datetime.now(UTC).isoformat(),
        "notice": "Simulation output; not empirical evidence.",
        "experiment": {
            "parameters": asdict(config),
            "seeds": [config.seed],
        },
        "model": {
            "package_version": package_version(),
            "metric_schema_version": METRIC_SCHEMA_VERSION,
            "git_commit": git_commit(),
            "git_dirty": git_dirty(),
        },
        "environment": {
            "python": platform.python_version(),
            "mesa": mesa_version(),
            "platform": platform.platform(),
        },
    }
