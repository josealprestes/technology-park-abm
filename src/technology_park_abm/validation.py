"""Pattern-oriented validation helpers (phase F5).

These functions measure stylized facts used to validate the simulation
qualitatively: heterogeneity, network clustering, and survival.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .network import TypedNetwork


def gini(values: Sequence[float]) -> float:
    """Gini coefficient of a non-negative distribution in [0, 1]."""
    if not values:
        return 0.0
    if any(value < 0.0 for value in values):
        raise ValueError("gini requires non-negative values")
    total = sum(values)
    if total == 0.0:
        return 0.0
    ordered = sorted(values)
    count = len(ordered)
    weighted = sum((index + 1) * value for index, value in enumerate(ordered))
    return (2.0 * weighted) / (count * total) - (count + 1) / count


def clustering_coefficient(network: TypedNetwork, agent_ids: Sequence[int]) -> float:
    """Global transitivity of partnership ties among the given agents."""
    nodes = set(agent_ids)
    if len(nodes) < 3:
        return 0.0
    adjacency: dict[int, set[int]] = {node: set() for node in nodes}
    for first, second, _strength in network.pairs("partnership"):
        if first in nodes and second in nodes:
            adjacency[first].add(second)
            adjacency[second].add(first)
    triangles = 0
    triples = 0
    for neighbors in adjacency.values():
        degree = len(neighbors)
        triples += degree * (degree - 1) // 2
        for other in neighbors:
            triangles += len(neighbors & adjacency[other])
    if triples == 0:
        return 0.0
    return triangles / (2.0 * triples)


def survival_rate(record: Mapping[str, Any]) -> float:
    """Share of created startups still active in a step record."""
    started = float(record["startup_count"])
    if started <= 0.0:
        return 0.0
    return float(record["active_startup_count"]) / started
