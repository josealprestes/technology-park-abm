import pytest

from technology_park_abm import ModelConfig, TechnologyParkModel

pytestmark = pytest.mark.e2e

ECOSYSTEM_CONFIG = ModelConfig(
    n_startups=6,
    n_anchor_firms=1,
    n_universities=1,
    n_investors=2,
    n_workers=4,
    anchor_participation="active",
    voluntary_exit_probability=0.01,
    migration_probability=0.01,
    acquisition_probability=0.01,
    acquisition_min_quality=0.05,
    seed=11,
)


def test_full_ecosystem_long_run_holds_invariants() -> None:
    model = TechnologyParkModel(config=ECOSYSTEM_CONFIG)
    record = model.metrics()
    for _ in range(300):
        record = model.advance()
        assert record["capital_total"] >= 0.0
        assert record["knowledge_total"] >= 0.0
        assert record["active_startup_count"] >= 0
        assert record["entry_count"] >= 0
        assert record["employment_total"] >= 0
        assert 0.0 <= record["reputation"] <= 1.0
        assert record["congestion"] >= 0.0
        for count in record["exit_count_by_type"].values():
            assert count >= 0
    assert record["period"] == 300


def test_same_seed_reproduces_the_full_history() -> None:
    first = TechnologyParkModel(config=ECOSYSTEM_CONFIG)
    second = TechnologyParkModel(config=ECOSYSTEM_CONFIG)
    first_history = [first.advance() for _ in range(100)]
    second_history = [second.advance() for _ in range(100)]
    assert first_history == second_history


def test_interleaved_runs_do_not_share_state() -> None:
    left = TechnologyParkModel(n_startups=4, seed=9)
    right = TechnologyParkModel(n_startups=4, seed=9)
    interleaved = []
    for _ in range(20):
        interleaved.append(left.advance())
        right.advance()
    reference = TechnologyParkModel(n_startups=4, seed=9)
    sequential = [reference.advance() for _ in range(20)]
    assert interleaved == sequential
