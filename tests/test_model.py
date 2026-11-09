from typing import Any, cast

from technology_park_abm import ModelConfig, ParkAuthority, TechnologyParkModel

REQUIRED_KEYS = {
    "period",
    "startup_count",
    "active_startup_count",
    "capital_total",
    "knowledge_total",
    "entry_count",
    "exit_count_by_type",
    "ties_formed_by_type",
    "active_tie_count",
    "partnership_tie_count",
    "productive_tie_count",
    "network_density",
    "degree_centralization",
    "knowledge_mean",
    "innovation_count",
    "innovation_cumulative",
    "quality_mean",
    "employment_total",
    "reputation",
    "congestion",
}


def test_model_is_reproducible_for_same_seed() -> None:
    first = TechnologyParkModel(n_startups=3, seed=7)
    second = TechnologyParkModel(n_startups=3, seed=7)
    assert [first.advance() for _ in range(5)] == [second.advance() for _ in range(5)]


def test_startups_exit_when_capital_is_exhausted() -> None:
    config = ModelConfig(
        n_startups=1,
        seed=1,
        initial_capital=100.0,
        entry_potential_per_period=0,
        rnd_share=0.0,
    )
    model = TechnologyParkModel(config=config)
    for _ in range(100):
        metrics = model.advance()
    assert metrics["active_startup_count"] == 0
    assert metrics["capital_total"] == 0.0
    assert metrics["exit_count_by_type"]["failure"] == 1


def test_metrics_before_first_step() -> None:
    model = TechnologyParkModel(n_startups=3, seed=0)
    record = model.metrics()
    assert record["period"] == 0
    assert record["active_startup_count"] == 3
    assert record["entry_count"] == 0
    assert record["capital_total"] > 0.0


def test_negative_population_is_rejected() -> None:
    try:
        TechnologyParkModel(n_startups=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative population should fail")


def test_non_integer_seed_is_rejected() -> None:
    try:
        TechnologyParkModel(config=ModelConfig(seed=cast(Any, 3.5)))
    except ValueError:
        pass
    else:
        raise AssertionError("non-integer seed should fail")


def test_relief_outside_unit_interval_is_rejected() -> None:
    try:
        TechnologyParkModel(config=ModelConfig(investor_burn_relief=1.5))
    except ValueError:
        pass
    else:
        raise AssertionError("relief outside [0, 1] should fail")


def test_zero_shock_nodes_is_rejected() -> None:
    try:
        TechnologyParkModel(config=ModelConfig(shock_nodes=0))
    except ValueError:
        pass
    else:
        raise AssertionError("zero shock nodes should fail")


def test_metrics_follow_contract_v1() -> None:
    config = ModelConfig(
        n_startups=4,
        seed=0,
        initial_capital=100.0,
        entry_potential_per_period=0,
        rnd_share=0.0,
    )
    model = TechnologyParkModel(config=config)
    record = model.advance()
    assert set(record) == REQUIRED_KEYS
    assert record["period"] == 1
    assert record["startup_count"] == 4
    assert record["active_startup_count"] == 4
    assert record["capital_total"] == 396.0
    assert record["knowledge_total"] == 0.0
    assert record["entry_count"] == 0
    assert record["exit_count_by_type"] == {
        "failure": 0,
        "acquisition": 0,
        "voluntary": 0,
        "migration": 0,
    }


def test_metrics_invariants_hold_over_time() -> None:
    model = TechnologyParkModel(n_startups=5, seed=3)
    for _ in range(200):
        record = model.advance()
        assert record["period"] >= 1
        assert record["active_startup_count"] >= 0
        assert record["capital_total"] >= 0.0
        assert record["knowledge_total"] >= 0.0
        assert record["knowledge_mean"] >= 0.0
        assert record["productive_tie_count"] >= 0
        assert 0.0 <= record["network_density"] <= 1.0
        assert 0.0 <= record["degree_centralization"] <= 1.0
        assert record["entry_count"] >= 0
        assert record["innovation_count"] >= 0
        assert record["employment_total"] >= 0
        assert 0.0 <= record["reputation"] <= 1.0
        assert record["congestion"] >= 0.0
        for count in record["exit_count_by_type"].values():
            assert count >= 0
        for count in record["ties_formed_by_type"].values():
            assert count >= 0


def test_config_overrides_keyword_arguments() -> None:
    config = ModelConfig(
        n_startups=2,
        seed=1,
        initial_capital=10.0,
        burn_rate=10.0,
        entry_potential_per_period=0,
        rnd_share=0.0,
    )
    model = TechnologyParkModel(config=config)
    record = model.advance()
    assert model.config is config
    assert record["active_startup_count"] == 0
    assert record["capital_total"] == 0.0


def test_run_for_matches_advance() -> None:
    via_advance = TechnologyParkModel(n_startups=2, seed=5)
    via_run_for = TechnologyParkModel(n_startups=2, seed=5)
    for _ in range(3):
        via_advance.advance()
    via_run_for.run_for(3)
    assert via_advance.metrics() == via_run_for.metrics()


def test_population_is_created_from_config() -> None:
    config = ModelConfig(
        n_startups=2,
        n_anchor_firms=1,
        n_universities=1,
        n_investors=1,
        n_workers=2,
        seed=0,
    )
    model = TechnologyParkModel(config=config)
    assert len(model.startups) == 2
    assert len(model.anchor_firms) == 1
    assert len(model.universities) == 1
    assert len(model.investors) == 1
    assert len(model.workers) == 2
    assert isinstance(model.authority, ParkAuthority)


def test_startup_sectors_follow_deterministic_round_robin() -> None:
    config = ModelConfig(n_startups=5, sectors=("alpha", "beta"), seed=0)
    model = TechnologyParkModel(config=config)
    assert [startup.sector for startup in model.startups] == [
        "alpha",
        "beta",
        "alpha",
        "beta",
        "alpha",
    ]
