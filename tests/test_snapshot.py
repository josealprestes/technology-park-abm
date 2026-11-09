import json

from technology_park_abm import ModelConfig, TechnologyParkModel


def test_snapshot_is_json_serializable() -> None:
    model = TechnologyParkModel(n_startups=3, seed=1)
    model.advance()
    json.dumps(model.snapshot())


def test_snapshot_is_reproducible_for_same_seed() -> None:
    first = TechnologyParkModel(n_startups=3, seed=1)
    second = TechnologyParkModel(n_startups=3, seed=1)
    for _ in range(5):
        first.advance()
        second.advance()
    assert first.snapshot() == second.snapshot()


def test_snapshot_contains_full_state() -> None:
    config = ModelConfig(n_startups=2, seed=2, entry_potential_per_period=0)
    model = TechnologyParkModel(config=config)
    model.advance()
    snapshot = model.snapshot()
    assert snapshot["period"] == 1
    assert len(snapshot["startups"]) == 2
    assert isinstance(snapshot["network"], list)
    assert snapshot["config"]["seed"] == 2
    assert "reputation" in snapshot["authority"]
    assert "sectors" in snapshot["environment"]


def test_snapshots_diverge_across_seeds() -> None:
    first = TechnologyParkModel(n_startups=3, seed=1)
    second = TechnologyParkModel(n_startups=3, seed=2)
    for _ in range(5):
        first.advance()
        second.advance()
    assert first.snapshot() != second.snapshot()
