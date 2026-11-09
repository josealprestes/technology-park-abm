"""Metamorphic relations for oracle-less verification and validation.

Parameter-change relations (verification): the direction of effect is known
even though exact outputs are not. Model-change relations (validation): adding
an element that the mechanism says is inert must not change outcomes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from technology_park_abm import ModelConfig, TechnologyParkModel


def _run(config: ModelConfig, periods: int = 10) -> Mapping[str, Any]:
    model = TechnologyParkModel(config=config)
    record: Mapping[str, Any] = model.metrics()
    for _ in range(periods):
        record = model.advance()
    return record


def test_mr_more_compatibility_weakly_increases_ties() -> None:
    base = ModelConfig(
        seed=5,
        n_startups=6,
        entry_potential_per_period=0,
        partnership_attempts_per_startup=2,
        partnership_base_probability=0.1,
        partnership_dissolution_probability=0.0,
    )
    low = _run(
        replace(
            base,
            same_sector_compatibility=0.2,
            cross_sector_compatibility=0.2,
        )
    )
    high = _run(
        replace(
            base,
            same_sector_compatibility=1.0,
            cross_sector_compatibility=1.0,
        )
    )
    assert high["partnership_tie_count"] >= low["partnership_tie_count"]


def test_mr_more_capacity_weakly_reduces_congestion_and_raises_capital() -> None:
    base = ModelConfig(
        seed=6,
        n_startups=10,
        entry_potential_per_period=0,
        infrastructure_capacity=5.0,
    )
    tight = _run(base)
    roomy = _run(replace(base, infrastructure_capacity=50.0))
    assert roomy["congestion"] <= tight["congestion"]
    assert roomy["capital_total"] >= tight["capital_total"]


def test_mr_passive_anchor_is_invisible_to_network_formation() -> None:
    base = ModelConfig(
        seed=7,
        n_startups=4,
        entry_potential_per_period=0,
        partnership_attempts_per_startup=2,
        partnership_cost_weight=0.0,
    )
    without = _run(base)
    with_passive = _run(replace(base, n_anchor_firms=1, anchor_participation="passive"))
    assert with_passive["partnership_tie_count"] == without["partnership_tie_count"]
    assert with_passive["active_startup_count"] == without["active_startup_count"]


def test_mr_more_capital_weakly_increases_survival() -> None:
    base = ModelConfig(
        seed=8,
        n_startups=5,
        entry_potential_per_period=0,
        initial_capital=50.0,
    )
    low = _run(base, periods=80)
    high = _run(replace(base, initial_capital=500.0), periods=80)
    assert high["active_startup_count"] >= low["active_startup_count"]
