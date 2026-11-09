"""Schema contracts for persisted experiment artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from technology_park_abm.experiments import persist_run, run_experiment_suite

REQUIRED_METRIC_COLUMNS = {
    "experiment",
    "scenario",
    "seed",
    "period",
    "active_startup_count",
    "capital_total",
    "knowledge_total",
    "knowledge_mean",
    "innovation_count",
    "partnership_tie_count",
    "entry_count",
    "exit_count_by_type_failure",
}


@pytest.mark.e2e
def test_persisted_artifacts_follow_their_schemas(tmp_path: Path) -> None:
    result = run_experiment_suite("E5", seeds=(0,), periods=2, run_id="contract")
    run_dir = persist_run(result, tmp_path)

    with (run_dir / "metrics.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = set(reader.fieldnames or [])
    assert REQUIRED_METRIC_COLUMNS <= fieldnames
    assert rows
    assert int(rows[0]["period"]) == 1

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    scenario = next(iter(summary.values()))
    metric = next(iter(scenario.values()))
    assert {"count", "mean", "min", "max", "median"} <= set(metric)

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0"
    assert manifest["run_id"] == "contract"
    assert "not empirical" in manifest["notice"].lower()
    assert manifest["experiment"]["periods"] == 2
    assert manifest["experiment"]["seeds"] == [0]
    assert manifest["model"]["metric_schema_version"] == "1.0"
    assert set(manifest["outputs"]) == {"metrics", "summary"}
