import pytest

from technology_park_abm import TypedNetwork


def test_add_and_query_ties() -> None:
    network = TypedNetwork()
    network.add_tie(2, 1, "partnership", 0.5)
    assert network.has_tie(1, 2, "partnership")
    assert network.has_tie(2, 1, "partnership")
    assert network.tie_strength(1, 2, "partnership") == 0.5
    assert network.tie_count() == 1
    assert network.tie_count("partnership") == 1
    assert network.tie_count("investment") == 0


def test_pairs_return_strength_in_insertion_order() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership", 0.25)
    network.add_tie(3, 2, "partnership", 0.75)
    assert network.pairs("partnership") == [(1, 2, 0.25), (2, 3, 0.75)]


def test_entries_include_tie_type() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership", 0.25)
    network.add_tie(3, 2, "investment", 1.0)
    assert network.entries() == [
        (1, 2, "partnership", 0.25),
        (2, 3, "investment", 1.0),
    ]


def test_remove_tie() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership")
    network.remove_tie(2, 1, "partnership")
    assert not network.has_tie(1, 2, "partnership")
    assert network.tie_count() == 0


def test_remove_agent_removes_all_incident_ties() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership")
    network.add_tie(1, 3, "investment")
    network.add_tie(2, 3, "hiring")
    network.remove_agent(1)
    assert network.tie_count() == 1
    assert network.has_tie(2, 3, "hiring")


def test_tie_strength_missing_raises_key_error() -> None:
    network = TypedNetwork()
    with pytest.raises(KeyError, match="tie not found"):
        network.tie_strength(1, 2, "partnership")


def test_self_tie_is_rejected() -> None:
    network = TypedNetwork()
    with pytest.raises(ValueError, match=r"^self ties are not allowed$"):
        network.add_tie(1, 1, "partnership")


def test_negative_strength_is_rejected() -> None:
    network = TypedNetwork()
    with pytest.raises(ValueError, match=r"^tie strength must be non-negative$"):
        network.add_tie(1, 2, "partnership", -0.1)


def test_add_tie_default_strength_is_one() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership")
    assert network.tie_strength(1, 2, "partnership") == 1.0


def test_remove_tie_missing_is_a_noop() -> None:
    network = TypedNetwork()
    network.add_tie(1, 2, "partnership")
    network.remove_tie(1, 3, "partnership")
    network.remove_tie(1, 2, "investment")
    assert network.tie_count() == 1
