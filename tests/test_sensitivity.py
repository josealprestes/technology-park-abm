import json
from pathlib import Path
from typing import Any

import pytest

from technology_park_abm import ModelConfig
from technology_park_abm.sensitivity import (
    build_report,
    history_matching,
    main,
    mean_outputs,
    morris_screen,
    one_at_a_time,
    seed_convergence,
    sobol_indices,
    two_way_interaction,
)


def test_one_at_a_time_structure() -> None:
    result = one_at_a_time(
        parameters=("burn_rate",),
        factors=(2.0,),
        seeds=(0,),
        periods=3,
        output_keys=("active_startup_count",),
    )
    assert set(result) == {"baseline", "variations"}
    assert "burn_rate=2" in result["variations"]
    variation = result["variations"]["burn_rate=2"]
    assert variation["parameter"] == "burn_rate"
    assert variation["factor"] == 2.0
    assert "active_startup_count" in variation["outputs"]


def test_one_at_a_time_is_deterministic() -> None:
    first = one_at_a_time(
        parameters=("burn_rate",),
        factors=(0.5,),
        seeds=(0,),
        periods=4,
        output_keys=("capital_total",),
    )
    second = one_at_a_time(
        parameters=("burn_rate",),
        factors=(0.5,),
        seeds=(0,),
        periods=4,
        output_keys=("capital_total",),
    )
    assert first == second


def test_mean_outputs_rejects_empty_seeds() -> None:
    try:
        mean_outputs(ModelConfig(), seeds=(), periods=3, output_keys=("capital_total",))
    except ValueError:
        pass
    else:
        raise AssertionError("empty seeds should fail")


def test_one_at_a_time_rejects_zero_periods() -> None:
    try:
        one_at_a_time(
            parameters=("burn_rate",),
            factors=(1.5,),
            seeds=(0,),
            periods=0,
            output_keys=("capital_total",),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("zero periods should fail")


def test_one_at_a_time_rejects_unknown_parameter() -> None:
    try:
        one_at_a_time(
            parameters=("unknown_parameter",),
            factors=(1.5,),
            seeds=(0,),
            periods=2,
            output_keys=("capital_total",),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("unknown parameter should fail")


def test_report_is_json_serializable_and_labeled() -> None:
    report = build_report(
        parameters=("burn_rate",),
        factors=(1.5,),
        seeds=(0,),
        periods=3,
        output_keys=("active_startup_count",),
    )
    json.dumps(report)
    assert "not empirical" in report["notice"].lower()


def test_two_way_interaction_structure() -> None:
    result = two_way_interaction(
        "burn_rate",
        2.0,
        "knowledge_spillover_rate",
        0.4,
        seeds=(0,),
        periods=3,
        output_keys=("capital_total",),
    )
    assert {"baseline", "only_a", "only_b", "both", "interaction"} <= set(result)
    assert result["parameter_a"] == "burn_rate"
    assert result["parameter_b"] == "knowledge_spillover_rate"


def test_two_way_interaction_is_deterministic() -> None:
    first = two_way_interaction(
        "burn_rate",
        2.0,
        "knowledge_spillover_rate",
        0.4,
        seeds=(0,),
        periods=4,
        output_keys=("capital_total",),
    )
    second = two_way_interaction(
        "burn_rate",
        2.0,
        "knowledge_spillover_rate",
        0.4,
        seeds=(0,),
        periods=4,
        output_keys=("capital_total",),
    )
    assert first == second


def test_two_way_interaction_rejects_unknown_parameter() -> None:
    try:
        two_way_interaction(
            "burn_rate",
            2.0,
            "unknown_parameter",
            1.0,
            seeds=(0,),
            periods=2,
            output_keys=("capital_total",),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("unknown parameter should fail")


@pytest.mark.e2e
def test_cli_writes_interaction_probe(tmp_path: Path) -> None:
    output = tmp_path / "interaction.json"
    exit_code = main(
        [
            "--parameters",
            "burn_rate",
            "--factors",
            "1.5",
            "--seeds",
            "0",
            "--periods",
            "3",
            "--interaction",
            "burn_rate",
            "2",
            "knowledge_spillover_rate",
            "0.4",
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "interaction" in payload


@pytest.mark.e2e
def test_morris_screen_structure_and_determinism() -> None:
    first = morris_screen(
        ("burn_rate", "initial_capital"),
        seeds=(0,),
        periods=2,
        output_keys=("capital_total",),
        trajectories=2,
        levels=3,
    )
    second = morris_screen(
        ("burn_rate", "initial_capital"),
        seeds=(0,),
        periods=2,
        output_keys=("capital_total",),
        trajectories=2,
        levels=3,
    )
    assert first == second
    effects = first["effects"]
    assert set(effects) == {"burn_rate", "initial_capital"}
    for metrics in effects.values():
        assert metrics["capital_total"]["mu_star"] >= 0.0
        assert metrics["capital_total"]["mu_star_range"] >= 0.0
        assert metrics["capital_total"]["sigma"] >= 0.0


def test_sobol_indices_structure_and_determinism() -> None:
    first = sobol_indices(
        parameters=("burn_rate", "knowledge_spillover_rate"),
        seeds=(0,),
        periods=2,
        output_keys=("capital_total",),
        samples=8,
    )
    second = sobol_indices(
        parameters=("burn_rate", "knowledge_spillover_rate"),
        seeds=(0,),
        periods=2,
        output_keys=("capital_total",),
        samples=8,
    )
    assert first == second
    indices = first["indices"]
    assert set(indices) == {"burn_rate", "knowledge_spillover_rate"}
    for metrics in indices.values():
        assert "first_order" in metrics["capital_total"]
        assert "total" in metrics["capital_total"]


def test_seed_convergence_structure() -> None:
    series = seed_convergence(
        "knowledge_total",
        periods=2,
        seed_counts=(2, 4),
    )
    assert len(series) == 2
    assert series[0]["seeds"] == 2.0
    assert series[1]["seeds"] == 4.0
    assert series[1]["stdev"] >= 0.0


def test_cli_writes_gsa_and_convergence(tmp_path: Path) -> None:
    output = tmp_path / "gsa.json"
    exit_code = main(
        [
            "--parameters",
            "burn_rate",
            "--factors",
            "1.5",
            "--seeds",
            "0",
            "--periods",
            "2",
            "--gsa",
            "morris",
            "--gsa-parameters",
            "burn_rate",
            "--convergence",
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "morris" in payload
    assert "convergence" in payload


def test_history_matching_shapes_and_budget() -> None:
    result = history_matching(
        parameters=("congestion_cost_per_org", "initial_capital"),
        seeds=(0, 1),
        periods=3,
        levels=3,
    )
    assert result["levels"] == 3
    assert result["evaluations"] == 3**2 * 2
    assert len(result["points"]) == 3**2
    assert result["ruled_out_count"] + result["not_ruled_out_count"] == len(
        result["points"]
    )
    for point in result["points"]:
        assert set(point) == {
            "parameters",
            "outputs",
            "implausibility",
            "ruled_out",
        }
        assert point["ruled_out"] == (point["implausibility"] > 3.0)


def test_history_matching_is_deterministic() -> None:
    first = history_matching(seeds=(0, 1), periods=3, levels=3)
    second = history_matching(seeds=(0, 1), periods=3, levels=3)
    assert first == second


def test_history_matching_rejects_bad_input() -> None:
    base: dict[str, Any] = {"periods": 3, "levels": 3, "seeds": (0,)}
    overrides: tuple[dict[str, Any], ...] = (
        {"periods": 0},
        {"levels": 1},
        {"seeds": ()},
    )
    for override in overrides:
        try:
            history_matching(**{**base, **override})
        except ValueError:
            pass
        else:
            raise AssertionError(f"bad input should fail: {override}")


def test_cli_history_matching_flag(tmp_path: Path) -> None:
    output = tmp_path / "sensitivity.json"
    exit_code = main(
        [
            "--parameters",
            "burn_rate",
            "--factors",
            "1.5",
            "--seeds",
            "0",
            "1",
            "--periods",
            "3",
            "--history-matching",
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "history_matching" in payload
    assert payload["history_matching"]["evaluations"] == 5**2 * 2


def test_cli_writes_report(tmp_path: Path) -> None:
    output = tmp_path / "sensitivity.json"
    exit_code = main(
        [
            "--parameters",
            "burn_rate",
            "--factors",
            "1.5",
            "--seeds",
            "0",
            "--periods",
            "3",
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "baseline" in payload
    assert "variations" in payload
