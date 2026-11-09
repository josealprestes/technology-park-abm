"""Byte-level reproduction of persisted experiment artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from technology_park_abm.experiments import persist_run, run_experiment_suite

pytestmark = pytest.mark.e2e


def test_persisted_experiment_is_byte_reproducible(tmp_path: Path) -> None:
    first = run_experiment_suite("E5", seeds=(1, 2), periods=3, run_id="repro-a")
    second = run_experiment_suite("E5", seeds=(1, 2), periods=3, run_id="repro-b")
    dir_a = persist_run(first, tmp_path)
    dir_b = persist_run(second, tmp_path)
    assert (dir_a / "metrics.csv").read_text(encoding="utf-8") == (
        dir_b / "metrics.csv"
    ).read_text(encoding="utf-8")
    assert (dir_a / "summary.json").read_text(encoding="utf-8") == (
        dir_b / "summary.json"
    ).read_text(encoding="utf-8")
