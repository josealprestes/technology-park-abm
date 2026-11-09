from pathlib import Path

import pytest

from technology_park_abm.experiments import (
    EXPERIMENT_IDS,
    build_experiments,
    main,
    persist_run,
    run_experiment_suite,
)


def test_all_experiments_build_with_at_least_two_scenarios() -> None:
    specs = build_experiments(periods=6)
    assert set(specs) == set(EXPERIMENT_IDS)
    for spec in specs.values():
        assert len(spec.scenarios) >= 2


def test_e6_scenarios_include_shock_configuration() -> None:
    specs = build_experiments(periods=10)
    scenarios = {scenario.name: scenario for scenario in specs["E6"].scenarios}
    assert scenarios["baseline"].config.shock_type is None
    assert scenarios["central_firm_collapse"].config.shock_period == 5
    assert scenarios["funding_collapse"].config.shock_type == "funding"


def test_run_suite_rejects_empty_seeds_or_periods() -> None:
    try:
        run_experiment_suite("E1", seeds=(), periods=3)
    except ValueError:
        pass
    else:
        raise AssertionError("empty seeds should fail")
    try:
        run_experiment_suite("E1", seeds=(0,), periods=0)
    except ValueError:
        pass
    else:
        raise AssertionError("zero periods should fail")


@pytest.mark.e2e
def test_run_suite_produces_rows_and_summary(tmp_path: Path) -> None:
    result = run_experiment_suite("E1", seeds=(0,), periods=3, run_id="test-e1")
    scenario_count = len(build_experiments(periods=3)["E1"].scenarios)
    assert len(result.rows) == scenario_count * 3
    assert len(result.summary) == scenario_count
    run_dir = persist_run(result, tmp_path)
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "metrics.csv").exists()
    assert (run_dir / "summary.json").exists()


def test_manifest_always_includes_run_id() -> None:
    result = run_experiment_suite("E5", seeds=(0,), periods=2)
    assert result.manifest["run_id"] == result.run_id


def test_manifest_records_scenario_playbooks() -> None:
    result = run_experiment_suite("E3", seeds=(0,), periods=2, run_id="playbooks")
    playbooks = result.manifest["experiment"]["playbooks"]
    assert playbooks["active"] == "anchor-led"
    assert playbooks["passive"] == "passive-anchor"
    assert playbooks["absent"] == "fragmented"


def test_run_suite_is_reproducible() -> None:
    first = run_experiment_suite("E5", seeds=(1,), periods=4, run_id="repeat")
    second = run_experiment_suite("E5", seeds=(1,), periods=4, run_id="repeat")
    assert first.rows == second.rows
    assert first.summary == second.summary


def test_manifest_is_labeled_as_simulation() -> None:
    result = run_experiment_suite("E3", seeds=(0,), periods=2, run_id="label")
    manifest = result.manifest
    assert "not empirical" in manifest["notice"].lower()
    assert manifest["experiment"]["seeds"] == [0]
    assert "passive" in manifest["experiment"]["scenarios"]


@pytest.mark.e2e
def test_cli_runs_end_to_end(tmp_path: Path) -> None:
    exit_code = main(
        ["E5", "--seeds", "0", "--periods", "3", "--output", str(tmp_path)]
    )
    assert exit_code == 0
    run_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "manifest.json").exists()


def test_e7_varies_distributedness_with_central_shock() -> None:
    specs = build_experiments(periods=10)
    scenarios = {scenario.name: scenario for scenario in specs["E7"].scenarios}
    assert set(scenarios) == {"hub", "distributed"}
    for scenario in scenarios.values():
        assert scenario.config.shock_period == 5
        assert scenario.config.shock_type == "central_firm"
        assert scenario.config.shock_nodes == 3
    # The distributedness axis: reputation-driven tie concentration.
    assert scenarios["hub"].config.partnership_reputation_weight == 0.6
    assert scenarios["distributed"].config.partnership_reputation_weight == 0.0


def test_e7_summary_carries_recovery_metrics() -> None:
    result = run_experiment_suite("E7", seeds=(1, 2, 3), periods=12, run_id="e7")
    for scenario in ("hub", "distributed"):
        summary = result.summary[scenario]
        for key in (
            "recovery_active_startup_count",
            "recovery_partnership_tie_count",
            "recovery_knowledge_total",
            "recovery_90pct",
            "baseline_degree_centralization",
        ):
            assert key in summary, f"{scenario} missing {key}"
        assert 0.0 <= summary["recovery_90pct"]["mean"] <= 1.0
        assert summary["recovery_90pct"]["min"] >= 0.0
        assert summary["recovery_90pct"]["max"] <= 1.0
        assert summary["recovery_active_startup_count"]["min"] >= 0.0


def test_e7_hub_is_more_centralized_than_distributed() -> None:
    # Simulation output for the fixed probe configuration (seeds 1-5,
    # 20 periods): the hub scenario concentrates ties on fewer startups
    # before the shock, which is the distributedness contrast H6 needs.
    result = run_experiment_suite("E7", seeds=(1, 2, 3, 4, 5), periods=20, run_id="e7")
    hub = result.summary["hub"]["baseline_degree_centralization"]["mean"]
    distributed = result.summary["distributed"]["baseline_degree_centralization"][
        "mean"
    ]
    assert hub > distributed


def test_e6_summary_also_carries_recovery_metrics() -> None:
    result = run_experiment_suite("E6", seeds=(1, 2), periods=10, run_id="e6")
    shocked = result.summary["central_firm_collapse"]
    assert "recovery_active_startup_count" in shocked
    assert "recovery_90pct" in shocked
    assert "baseline_degree_centralization" in shocked
    # The unshocked baseline scenario has no recovery metrics.
    assert "recovery_90pct" not in result.summary["baseline"]


def test_summary_distributions_include_p10_and_p90() -> None:
    result = run_experiment_suite("E1", seeds=(1, 2, 3), periods=4, run_id="p1090")
    for scenario_summary in result.summary.values():
        for stats in scenario_summary.values():
            assert "p10" in stats
            assert "p90" in stats
            assert stats["min"] <= stats["p10"] <= stats["median"]
            assert stats["median"] <= stats["p90"] <= stats["max"]


def test_summary_quantiles_stay_within_sample_range() -> None:
    # Inclusive (numpy-compatible) quantiles never interpolate outside
    # [min, max], even for tiny samples such as a 0/1 recovery indicator.
    result = run_experiment_suite("E7", seeds=(1, 2, 3), periods=12, run_id="q")
    stats = result.summary["hub"]["recovery_90pct"]
    assert stats["min"] <= stats["p10"] <= stats["p90"] <= stats["max"]


def test_run_suite_rejects_invalid_jobs() -> None:
    try:
        run_experiment_suite("E1", seeds=(1,), periods=2, jobs=0)
    except ValueError:
        pass
    else:
        raise AssertionError("jobs=0 should fail")


def test_parallel_jobs_produce_identical_results() -> None:
    sequential = run_experiment_suite("E1", seeds=(1, 2), periods=4, run_id="par")
    parallel = run_experiment_suite("E1", seeds=(1, 2), periods=4, run_id="par", jobs=2)
    assert sequential.rows == parallel.rows
    assert sequential.summary == parallel.summary


def test_cli_accepts_jobs_flag(tmp_path: Path) -> None:
    exit_code = main(
        [
            "E5",
            "--seeds",
            "0",
            "--periods",
            "3",
            "--jobs",
            "2",
            "--output",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    run_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "summary.json").exists()


def test_cli_rejects_invalid_jobs(tmp_path: Path) -> None:
    try:
        main(
            [
                "E5",
                "--seeds",
                "0",
                "--periods",
                "3",
                "--jobs",
                "0",
                "--output",
                str(tmp_path),
            ]
        )
    except SystemExit:
        pass
    else:
        raise AssertionError("--jobs 0 should exit with an error")
