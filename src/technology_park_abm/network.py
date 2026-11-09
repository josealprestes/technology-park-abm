"""Typed, weighted, undirected network of relationships between agents."""

from __future__ import annotations


class TypedNetwork:
    """Undirected tie layers keyed by (lower id, higher id, tie type).

    Tie types are semantic labels such as "partnership", "investment", or
    "hiring". Strength is a non-negative measurable weight.
    """

    def __init__(self) -> None:
        self._ties: dict[tuple[int, int, str], float] = {}

    def add_tie(
        self,
        first: int,
        second: int,
        tie_type: str,
        strength: float = 1.0,
    ) -> None:
        if first == second:
            raise ValueError("self ties are not allowed")
        if strength < 0.0:
            raise ValueError("tie strength must be non-negative")
        self._ties[_pair(first, second) + (tie_type,)] = strength

    def remove_tie(self, first: int, second: int, tie_type: str) -> None:
        self._ties.pop(_pair(first, second) + (tie_type,), None)

    def has_tie(self, first: int, second: int, tie_type: str) -> bool:
        return _pair(first, second) + (tie_type,) in self._ties

    def tie_strength(self, first: int, second: int, tie_type: str) -> float:
        key = _pair(first, second) + (tie_type,)
        if key not in self._ties:
            raise KeyError(f"tie not found: {key}")
        return self._ties[key]

    def tie_count(self, tie_type: str | None = None) -> int:
        if tie_type is None:
            return len(self._ties)
        return sum(1 for _, _, stored_type in self._ties if stored_type == tie_type)

    def pairs(self, tie_type: str | None = None) -> list[tuple[int, int, float]]:
        """Return (first, second, strength) in deterministic insertion order."""
        return [
            (first, second, strength)
            for (first, second, stored_type), strength in self._ties.items()
            if tie_type is None or stored_type == tie_type
        ]

    def entries(self) -> list[tuple[int, int, str, float]]:
        """Return (first, second, tie_type, strength) in insertion order."""
        return [
            (first, second, tie_type, strength)
            for (first, second, tie_type), strength in self._ties.items()
        ]

    def remove_agent(self, agent_id: int) -> None:
        for key in [
            key for key in self._ties if agent_id == key[0] or agent_id == key[1]
        ]:
            del self._ties[key]


def _pair(first: int, second: int) -> tuple[int, int]:
    return (first, second) if first < second else (second, first)
