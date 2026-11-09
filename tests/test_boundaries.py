"""Boundary and edge-case configurations run and preserve invariants."""

from __future__ import annotations

import json

import pytest

from technology_park_abm import ModelConfig, TechnologyParkModel

CASES: dict[str, ModelConfig] = {
    "zero_capacity": ModelConfig(infrastructure_capacity=0.0),
    "zero_capital": ModelConfig(initial_capital=0.0),
    "zero_burn": ModelConfig(burn_rate=0.0),
    "empty_entry_off": ModelConfig(n_startups=0, entry_potential_per_period=0),
    "empty_entry_on": ModelConfig(n_startups=0),
    "zero_team_max": ModelConfig(max_team_size=0),
    "huge_values": ModelConfig(
        knowledge_rnd_gain=1000.0,
        entry_potential_per_period=50,
    ),
    "shock_no_targets": ModelConfig(
        n_startups=0,
        entry_potential_per_period=0,
        shock_period=1,
        shock_type="central_firm",
    ),
    "shock_funding_no_investors": ModelConfig(
        n_startups=1,
        shock_period=1,
        shock_type="funding",
    ),
    "shock_beyond_horizon": ModelConfig(
        n_startups=2,
        entry_potential_per_period=0,
        shock_period=500,
        shock_type="central_firm",
    ),
    "zero_compatibility": ModelConfig(
        cross_sector_compatibility=0.0,
        cross_sector_complementarity=0.0,
    ),
    "huge_congestion": ModelConfig(congestion_cost_per_org=1000.0),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_boundary_configurations_run_and_preserve_invariants(name: str) -> None:
    model = TechnologyParkModel(config=CASES[name])
    record = model.metrics()
    for _ in range(10):
        record = model.advance()
        assert record["capital_total"] >= 0.0
        assert record["knowledge_total"] >= 0.0
        assert record["active_startup_count"] >= 0
        assert 0.0 <= record["reputation"] <= 1.0
        assert record["congestion"] >= 0.0
        total_exits = sum(record["exit_count_by_type"].values())
        assert total_exits >= 0
    json.dumps(model.snapshot())


def test_seed_none_runs_without_error() -> None:
    model = TechnologyParkModel(config=ModelConfig(seed=None, n_startups=2))
    for _ in range(3):
        model.advance()
    assert model.metrics()["period"] == 3
