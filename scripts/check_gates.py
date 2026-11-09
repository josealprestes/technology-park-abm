"""Single deterministic gate runner (see AGENTS.md).

Runs the repository quality gates in order: lint, format check, strict type
check, and the full test suite with warnings as errors and the coverage floor.
Every gate uses the current interpreter so the command works on any platform:

    python scripts/check_gates.py [--only lint,types]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

GATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("lint", ("-m", "ruff", "check", ".")),
    ("format", ("-m", "ruff", "format", "--check", ".")),
    ("types", ("-m", "mypy")),
    (
        "tests",
        (
            "-m",
            "pytest",
            "-q",
            "-W",
            "error::DeprecationWarning",
            "-W",
            "error::FutureWarning",
            "--cov",
            "--cov-report=term-missing",
        ),
    ),
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        default="",
        help="comma-separated subset of gate names (default: all)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the selected gates in order; return 0 only when all pass."""
    args = _parse_args(argv)
    only_raw: str = args.only
    names = [name for name, _ in GATES]
    wanted = [part.strip() for part in only_raw.split(",") if part.strip()]
    selected = wanted or names
    unknown = [name for name in selected if name not in names]
    if unknown:
        print(f"unknown gates: {', '.join(unknown)} (available: {', '.join(names)})")
        return 2
    failures: list[str] = []
    for name, command in GATES:
        if name not in selected:
            continue
        print(f"--- gate: {name} ---", flush=True)
        result = subprocess.run([sys.executable, *command], cwd=REPO_ROOT, check=False)
        if result.returncode != 0:
            failures.append(name)
            print(f"FAIL: {name} (exit {result.returncode})")
        else:
            print(f"PASS: {name}")
    if failures:
        print(f"gates failed: {', '.join(failures)}")
        return 1
    print(f"all gates green: {', '.join(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
