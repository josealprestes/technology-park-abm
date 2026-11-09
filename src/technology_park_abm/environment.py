"""Environment state: sectors, infrastructure, markets, and policy."""

from __future__ import annotations

from dataclasses import dataclass

from .config import ModelConfig, Policy


@dataclass
class SectorSpace:
    """Sector set with compatibility and complementarity lookups.

    Compatibility is coordination ease between two sectors in [0, 1].
    Complementarity is the potential knowledge gain from collaboration in
    [0, 1]. Same-sector and cross-sector values are configurable calibration
    placeholders, not empirical claims.
    """

    sectors: tuple[str, ...]
    same_sector_compatibility: float = 1.0
    cross_sector_compatibility: float = 0.25
    same_sector_complementarity: float = 0.5
    cross_sector_complementarity: float = 0.5

    def __post_init__(self) -> None:
        if not self.sectors:
            raise ValueError("at least one sector is required")
        for name, value in (
            ("same_sector_compatibility", self.same_sector_compatibility),
            ("cross_sector_compatibility", self.cross_sector_compatibility),
            ("same_sector_complementarity", self.same_sector_complementarity),
            ("cross_sector_complementarity", self.cross_sector_complementarity),
        ):
            self._require_unit_interval(name, value)

    def compatibility(self, first: str, second: str) -> float:
        """Coordination ease between two sectors in [0, 1]."""
        self._require_known(first)
        self._require_known(second)
        if first == second:
            return self.same_sector_compatibility
        return self.cross_sector_compatibility

    def complementarity(self, first: str, second: str) -> float:
        """Potential knowledge gain from collaboration in [0, 1]."""
        self._require_known(first)
        self._require_known(second)
        if first == second:
            return self.same_sector_complementarity
        return self.cross_sector_complementarity

    def _require_known(self, sector: str) -> None:
        if sector not in self.sectors:
            raise ValueError(f"unknown sector: {sector}")

    @staticmethod
    def _require_unit_interval(name: str, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0, 1]")


@dataclass
class Environment:
    """Mutable environment conditions shared by all agents."""

    sector_space: SectorSpace
    infrastructure_capacity: float = 1.0
    infrastructure_load: float = 0.0
    funding_conditions: float = 1.0
    labor_market_slack: float = 1.0
    policy: Policy = Policy()

    def __post_init__(self) -> None:
        for name, value in (
            ("infrastructure_capacity", self.infrastructure_capacity),
            ("infrastructure_load", self.infrastructure_load),
            ("funding_conditions", self.funding_conditions),
            ("labor_market_slack", self.labor_market_slack),
        ):
            if value < 0.0:
                raise ValueError(f"{name} must be non-negative")

    @classmethod
    def from_config(cls, config: ModelConfig) -> Environment:
        """Build the environment from a model configuration."""
        return cls(
            sector_space=SectorSpace(
                sectors=config.sectors,
                same_sector_compatibility=config.same_sector_compatibility,
                cross_sector_compatibility=config.cross_sector_compatibility,
                same_sector_complementarity=config.same_sector_complementarity,
                cross_sector_complementarity=config.cross_sector_complementarity,
            ),
            infrastructure_capacity=config.infrastructure_capacity,
            funding_conditions=config.funding_conditions,
            labor_market_slack=config.labor_market_slack,
            policy=config.policy,
        )
