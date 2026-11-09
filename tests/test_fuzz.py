import json
import random
from typing import Any

from technology_park_abm import SHOCK_TYPES, ModelConfig, Policy, TechnologyParkModel

POLICY_FIELDS = (
    "entry_subsidy",
    "rnd_subsidy",
    "shared_infrastructure",
    "matchmaking",
    "talent_program",
)


def _random_config(rng: random.Random) -> ModelConfig:
    values: dict[str, Any] = {
        "n_startups": rng.randint(0, 8),
        "n_anchor_firms": rng.randint(0, 2),
        "n_universities": rng.randint(0, 2),
        "n_investors": rng.randint(0, 2),
        "n_workers": rng.randint(0, 4),
        "entry_potential_per_period": rng.randint(0, 3),
        "initial_capital": rng.choice([50.0, 150.0, 300.0]),
        "burn_rate": rng.choice([0.5, 1.0, 2.0]),
        "infrastructure_capacity": rng.choice([2.0, 8.0, 50.0]),
        "partnership_attempts_per_startup": rng.randint(0, 3),
        "rnd_share": rng.random(),
        "knowledge_spillover_rate": rng.random(),
        "knowledge_depreciation": rng.random(),
        "hiring_probability": rng.random(),
        "investment_probability": rng.random(),
        "voluntary_exit_probability": rng.random() * 0.3,
        "migration_probability": rng.random() * 0.3,
        "acquisition_probability": rng.random() * 0.3,
        "congestion_cost_per_org": rng.choice([0.0, 1.0, 3.0]),
        "anchor_participation": rng.choice(["passive", "active"]),
        "seed": rng.randint(0, 10_000),
    }
    if rng.random() < 0.3:
        values["shock_period"] = rng.randint(1, 5)
        values["shock_type"] = rng.choice(SHOCK_TYPES)
    policy_values: dict[str, float] = {}
    for field_name in POLICY_FIELDS:
        if rng.random() < 0.3:
            policy_values[field_name] = rng.random()
    if rng.random() < 0.2:
        policy_values["investment_fund"] = rng.choice([50.0, 200.0])
    values["policy"] = Policy(**policy_values)
    return ModelConfig(**values)


def test_random_configurations_preserve_invariants() -> None:
    rng = random.Random(20261006)
    for _ in range(30):
        config = _random_config(rng)
        model = TechnologyParkModel(config=config)
        total_exits = 0
        record = model.metrics()
        for _ in range(12):
            record = model.advance()
            total_exits += sum(record["exit_count_by_type"].values())
            assert record["capital_total"] >= 0.0
            assert record["knowledge_total"] >= 0.0
            assert record["active_startup_count"] >= 0
            assert 0.0 <= record["reputation"] <= 1.0
            assert record["congestion"] >= 0.0
        assert record["startup_count"] - record["active_startup_count"] == total_exits


def test_random_configurations_produce_serializable_snapshots() -> None:
    rng = random.Random(42)
    for _ in range(10):
        model = TechnologyParkModel(config=_random_config(rng))
        for _ in range(4):
            model.advance()
        json.dumps(model.snapshot())
