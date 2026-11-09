"""Metric helpers, network summaries, and increasing-returns diagnostics.

The metric schema version follows the contract in docs/adr/0002. Additive
changes keep the version; breaking changes require a new version and ADR.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .network import TypedNetwork

METRIC_SCHEMA_VERSION = "1.0"

TREND_INCREASING = "increasing"
TREND_DECREASING = "decreasing"
TREND_NONE = "no_trend"


@dataclass(frozen=True)
class TrendResult:
    """Mann-Kendall trend test outcome with Sen's slope."""

    tau: float
    z: float
    p_value: float
    slope: float
    trend: str


def partnership_density(network: TypedNetwork, agent_ids: Sequence[int]) -> float:
    """Share of realized partnership ties among possible agent pairs."""
    node_ids = sorted(set(agent_ids))
    count = len(node_ids)
    if count < 2:
        return 0.0
    present = set(node_ids)
    realized = sum(
        1
        for first, second, _strength in network.pairs("partnership")
        if first in present and second in present
    )
    possible = count * (count - 1) / 2
    return realized / possible


def degree_centralization(network: TypedNetwork, agent_ids: Sequence[int]) -> float:
    """Freeman degree centralization of partnership ties among agents."""
    node_ids = sorted(set(agent_ids))
    count = len(node_ids)
    if count < 3:
        return 0.0
    present = set(node_ids)
    degrees = {node_id: 0 for node_id in node_ids}
    for first, second, _strength in network.pairs("partnership"):
        if first in present and second in present:
            degrees[first] += 1
            degrees[second] += 1
    max_degree = max(degrees.values())
    numerator = sum(max_degree - degree for degree in degrees.values())
    denominator = (count - 1) * (count - 2)
    return numerator / denominator


def productive_tie_count(network: TypedNetwork, min_strength: float) -> int:
    """Count partnership ties whose strength reaches a threshold."""
    return sum(
        1
        for _first, _second, strength in network.pairs("partnership")
        if strength >= min_strength
    )


def marginal_output(
    records: Sequence[Mapping[str, int | float]],
    output_key: str,
    population_key: str = "active_startup_count",
) -> list[tuple[int, float]]:
    """Compute marginal output per additional agent between consecutive periods.

    Returns (period, delta output / delta population) pairs; periods without a
    population change are skipped. Rising values over a range of system size
    indicate increasing returns; falling values indicate saturation.
    """
    series: list[tuple[int, float]] = []
    for previous, current in zip(records, records[1:], strict=False):
        delta_population = float(current[population_key]) - float(
            previous[population_key]
        )
        if delta_population == 0.0:
            continue
        delta_output = float(current[output_key]) - float(previous[output_key])
        series.append((int(current["period"]), delta_output / delta_population))
    return series


def mann_kendall_trend(series: Sequence[float], alpha: float = 0.05) -> TrendResult:
    """Mann-Kendall monotonic trend test with tie correction and Sen's slope.

    Non-parametric test for a monotonic trend in a time series. The test
    statistic S counts concordant minus discordant pairs; its variance
    carries the standard tie correction; the z score uses the normal
    approximation with continuity correction, and the two-sided p-value
    comes from the normal CDF (``math.erfc``, no SciPy dependency). Sen's
    slope is the median of all pairwise slopes. ``tau`` is Kendall's tau-a
    (no tie adjustment).

    A significant increasing trend (``trend == "increasing"``) with a
    positive slope is the statistical signature of rising returns; a
    significant decreasing trend indicates saturation.
    """
    values = [float(value) for value in series]
    count = len(values)
    if count < 2:
        return TrendResult(tau=0.0, z=0.0, p_value=1.0, slope=0.0, trend=TREND_NONE)
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    concordant = 0
    for first in range(count - 1):
        for second in range(first + 1, count):
            difference = values[second] - values[first]
            if difference > 0.0:
                concordant += 1
            elif difference < 0.0:
                concordant -= 1
    statistic = concordant
    tie_groups: dict[float, int] = {}
    for value in values:
        tie_groups[value] = tie_groups.get(value, 0) + 1
    tie_correction = sum(
        size * (size - 1) * (2 * size + 5) for size in tie_groups.values()
    )
    variance = (count * (count - 1) * (2 * count + 5) - tie_correction) / 18.0
    if variance <= 0.0:
        z_score = 0.0
    elif statistic > 0:
        z_score = (statistic - 1) / math.sqrt(variance)
    elif statistic < 0:
        z_score = (statistic + 1) / math.sqrt(variance)
    else:
        z_score = 0.0
    p_value = math.erfc(abs(z_score) / math.sqrt(2.0))
    tau = statistic / (count * (count - 1) / 2.0)
    slopes = [
        (values[second] - values[first]) / (second - first)
        for first in range(count - 1)
        for second in range(first + 1, count)
    ]
    slope = statistics.median(slopes)
    if p_value < alpha and statistic > 0:
        trend = TREND_INCREASING
    elif p_value < alpha and statistic < 0:
        trend = TREND_DECREASING
    else:
        trend = TREND_NONE
    return TrendResult(tau=tau, z=z_score, p_value=p_value, slope=slope, trend=trend)


def marginal_output_trend(
    records: Sequence[Mapping[str, int | float]],
    output_key: str,
    population_key: str = "active_startup_count",
    alpha: float = 0.05,
) -> TrendResult:
    """Mann-Kendall test over the marginal-output series (increasing returns).

    Runs :func:`mann_kendall_trend` on the marginal output per additional
    agent (see :func:`marginal_output`). A significant increasing trend means
    returns rise with system size (increasing returns); a significant
    decreasing trend means saturation. Series without any population change
    yield ``no_trend``.
    """
    series = marginal_output(records, output_key, population_key)
    return mann_kendall_trend([value for _period, value in series], alpha=alpha)
