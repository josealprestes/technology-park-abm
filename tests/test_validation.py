import pytest

from technology_park_abm import TechnologyParkModel, TypedNetwork
from technology_park_abm.validation import (
    clustering_coefficient,
    gini,
    survival_rate,
)


def test_gini_is_zero_for_equal_values() -> None:
    assert gini([10.0, 10.0, 10.0]) == 0.0


def test_gini_is_positive_for_inequality() -> None:
    assert gini([0.0, 0.0, 100.0]) > 0.5


def test_gini_handles_empty_and_zero_totals() -> None:
    assert gini([]) == 0.0
    assert gini([0.0, 0.0]) == 0.0


def test_gini_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match=r"^gini requires non-negative values$"):
        gini([-1.0, 2.0])


def test_gini_exact_value() -> None:
    # ordered [0, 0, 100]: 2*300/(3*100) - 4/3 = 2/3
    assert gini([0.0, 0.0, 100.0]) == pytest.approx(2.0 / 3.0)


def test_clustering_coefficient_triangle_and_path() -> None:
    triangle = TypedNetwork()
    triangle.add_tie(1, 2, "partnership", 1.0)
    triangle.add_tie(2, 3, "partnership", 1.0)
    triangle.add_tie(1, 3, "partnership", 1.0)
    assert clustering_coefficient(triangle, [1, 2, 3]) == 1.0
    path = TypedNetwork()
    path.add_tie(1, 2, "partnership", 1.0)
    path.add_tie(2, 3, "partnership", 1.0)
    assert clustering_coefficient(path, [1, 2, 3]) == 0.0
    assert clustering_coefficient(path, [1, 2]) == 0.0


def test_survival_rate() -> None:
    record: dict[str, int | float] = {
        "startup_count": 10,
        "active_startup_count": 6,
    }
    assert survival_rate(record) == 0.6
    assert survival_rate({"startup_count": 0, "active_startup_count": 0}) == 0.0


def test_survival_rate_with_a_single_startup() -> None:
    record: dict[str, int | float] = {"startup_count": 1, "active_startup_count": 1}
    assert survival_rate(record) == 1.0


def test_clustering_coefficient_without_ties_is_zero() -> None:
    network = TypedNetwork()
    assert clustering_coefficient(network, [1, 2, 3]) == 0.0


def test_clustering_coefficient_ignores_ties_with_outsiders() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership", 1.0)
    network.add_tie(2, 4, "partnership", 1.0)
    # Node 4 is outside the agent set: only the (1, 2) tie counts, leaving
    # one triple and no triangles.
    assert clustering_coefficient(network, [1, 2, 3]) == 0.0


def test_clustering_coefficient_counts_only_partnership_ties() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership", 1.0)
    network.add_tie(2, 3, "investment", 1.0)
    network.add_tie(1, 3, "investment", 1.0)
    # Only the partnership tie counts: one triple, no triangles.
    assert clustering_coefficient(network, [1, 2, 3]) == 0.0


def test_stylized_run_reproduces_qualitative_patterns() -> None:
    model = TechnologyParkModel(seed=42)
    record = model.metrics()
    for _ in range(80):
        record = model.advance()
    active = model.active_startups
    agent_ids = [startup.startup_id for startup in active]
    assert 0.0 < survival_rate(record) < 1.0
    assert gini([startup.capital for startup in active]) > 0.0
    assert clustering_coefficient(model.network, agent_ids) > 0.0
    assert record["partnership_tie_count"] > 0
    assert record["startup_count"] > 10
    assert record["knowledge_total"] > 0.0
