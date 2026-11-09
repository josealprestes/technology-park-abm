"""Statistical oracles for stochastic mechanisms (rates within intervals)."""

from __future__ import annotations

from dataclasses import replace

from technology_park_abm import ModelConfig, TechnologyParkModel


def test_entry_rate_matches_binomial_expectation() -> None:
    config = ModelConfig(
        n_startups=0,
        seed=1,
        entry_potential_per_period=100,
        entry_base_probability=0.5,
        entry_reputation_weight=0.0,
        entry_funding_weight=0.0,
        entry_infrastructure_weight=0.0,
        entry_opportunity_weight=0.0,
        entry_cost_weight=0.0,
    )
    total_entries = 0
    periods = 5
    seeds = 20
    for seed in range(1, seeds + 1):
        model = TechnologyParkModel(config=replace(config, seed=seed))
        record = model.metrics()
        for _ in range(periods):
            record = model.advance()
        total_entries += record["startup_count"]
    mean_per_period = total_entries / (seeds * periods)
    standard_deviation = (100 * 0.5 * 0.5) ** 0.5
    assert abs(mean_per_period - 50.0) < 3.0 * standard_deviation


def test_partnerships_reach_complete_graph_when_probability_is_one() -> None:
    config = ModelConfig(
        n_startups=4,
        seed=0,
        entry_potential_per_period=0,
        partnership_attempts_per_startup=3,
        partnership_base_probability=1.0,
        partnership_dissolution_probability=0.0,
    )
    model = TechnologyParkModel(config=config)
    record = model.metrics()
    for _ in range(10):
        record = model.advance()
    assert record["partnership_tie_count"] == 6


def test_voluntary_exit_rate_matches_expectation() -> None:
    config = ModelConfig(
        n_startups=50,
        seed=2,
        entry_potential_per_period=0,
        voluntary_exit_probability=0.2,
        rnd_share=0.0,
    )
    record = TechnologyParkModel(config=config).advance()
    exits = record["exit_count_by_type"]["voluntary"]
    standard_deviation = (50 * 0.2 * 0.8) ** 0.5
    assert abs(exits - 10.0) < 3.0 * standard_deviation
