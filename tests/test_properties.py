"""Property-based tests (Hypothesis) for core invariants and round-trips."""

from __future__ import annotations

import math

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from technology_park_abm import (
    ModelConfig,
    TechnologyParkModel,
    TypedNetwork,
    mann_kendall_trend,
)
from technology_park_abm.workbench_core import config_from_params, effective_params

SETTINGS = settings(max_examples=25, deadline=None, derandomize=True)


@given(
    first=st.integers(min_value=0, max_value=50),
    second=st.integers(min_value=0, max_value=50),
    strength=st.floats(
        min_value=0.0,
        max_value=10.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@SETTINGS
def test_network_tie_round_trip(first: int, second: int, strength: float) -> None:
    assume(first != second)
    network = TypedNetwork()
    network.add_tie(first, second, "partnership", strength)
    assert network.has_tie(second, first, "partnership")
    assert network.tie_strength(first, second, "partnership") == strength
    network.remove_tie(first, second, "partnership")
    assert not network.has_tie(first, second, "partnership")
    assert network.tie_count() == 0


@given(
    n_startups=st.integers(min_value=0, max_value=12),
    burn_rate=st.floats(
        min_value=0.0,
        max_value=5.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    matchmaking=st.floats(
        min_value=0.0,
        max_value=1.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
@SETTINGS
def test_config_params_round_trip(
    n_startups: int,
    burn_rate: float,
    matchmaking: float,
) -> None:
    config = config_from_params(
        {
            "n_startups": n_startups,
            "burn_rate": burn_rate,
            "policy__matchmaking": matchmaking,
        }
    )
    rebuilt = config_from_params(effective_params(config))
    assert rebuilt == config


@given(
    n_startups=st.integers(min_value=0, max_value=6),
    entry_potential=st.integers(min_value=0, max_value=3),
    exit_probability=st.floats(
        min_value=0.0,
        max_value=0.3,
        allow_nan=False,
        allow_infinity=False,
    ),
    seed=st.integers(min_value=0, max_value=10_000),
)
@SETTINGS
def test_model_conservation_property(
    n_startups: int,
    entry_potential: int,
    exit_probability: float,
    seed: int,
) -> None:
    config = ModelConfig(
        n_startups=n_startups,
        entry_potential_per_period=entry_potential,
        voluntary_exit_probability=exit_probability,
        seed=seed,
    )
    model = TechnologyParkModel(config=config)
    total_exits = 0
    record = model.metrics()
    for _ in range(4):
        record = model.advance()
        total_exits += sum(record["exit_count_by_type"].values())
        assert record["capital_total"] >= 0.0
        assert record["active_startup_count"] >= 0
    assert record["startup_count"] - record["active_startup_count"] == total_exits


@given(
    series=st.lists(
        st.floats(
            min_value=-1e6,
            max_value=1e6,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=2,
        max_size=12,
    )
)
@SETTINGS
def test_mann_kendall_result_ranges(series: list[float]) -> None:
    result = mann_kendall_trend(series)
    assert -1.0 <= result.tau <= 1.0
    assert 0.0 <= result.p_value <= 1.0
    assert result.trend in {"increasing", "decreasing", "no_trend"}
    assert math.isfinite(result.z)
    assert math.isfinite(result.slope)


@given(
    series=st.lists(
        st.floats(
            min_value=-1e6,
            max_value=1e6,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=2,
        max_size=12,
    )
)
@SETTINGS
def test_mann_kendall_reversal_symmetry(series: list[float]) -> None:
    forward = mann_kendall_trend(series)
    backward = mann_kendall_trend(list(reversed(series)))
    assert math.isclose(backward.tau, -forward.tau, rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(backward.z, -forward.z, rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(backward.p_value, forward.p_value, rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(backward.slope, -forward.slope, rel_tol=1e-9, abs_tol=1e-12)
    flip = {
        "increasing": "decreasing",
        "decreasing": "increasing",
        "no_trend": "no_trend",
    }
    assert backward.trend == flip[forward.trend]


@given(n=st.integers(min_value=5, max_value=12))
@SETTINGS
def test_mann_kendall_strictly_monotonic_is_detected(n: int) -> None:
    up = mann_kendall_trend([float(i) for i in range(n)])
    assert up.trend == "increasing"
    assert up.slope > 0.0
    assert up.tau > 0.0
    down = mann_kendall_trend([float(i) for i in range(n, 0, -1)])
    assert down.trend == "decreasing"
    assert down.slope < 0.0
    assert down.tau < 0.0


@given(n=st.integers(min_value=2, max_value=12))
@SETTINGS
def test_mann_kendall_constant_series_is_no_trend(n: int) -> None:
    result = mann_kendall_trend([3.5] * n)
    assert result.trend == "no_trend"
    assert result.tau == 0.0
    assert result.slope == 0.0
    assert result.p_value == 1.0
