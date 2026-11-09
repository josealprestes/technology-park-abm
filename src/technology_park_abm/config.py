"""Configuration objects and deterministic random-stream derivation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

DEFAULT_SECTORS: tuple[str, ...] = ("biotech", "energy", "hardware", "software")

SHOCK_TYPES: tuple[str, ...] = ("central_firm", "funding")

STREAM_NAMES: tuple[str, ...] = (
    "entry",
    "partnerships",
    "knowledge",
    "finance",
    "exit",
    "reputation",
)


def derive_stream_seed(seed: int, stream: str) -> int:
    """Derive an independent sub-seed from a master seed and stream name.

    Derivation uses SHA-256 so results are stable across platforms and Python
    versions, unlike hash().
    """
    digest = hashlib.sha256(f"{seed}:{stream}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


@dataclass(frozen=True)
class Policy:
    """Policy instruments available to the park authority (experiment E4)."""

    entry_subsidy: float = 0.0
    rnd_subsidy: float = 0.0
    shared_infrastructure: float = 0.0
    matchmaking: float = 0.0
    talent_program: float = 0.0
    investment_fund: float = 0.0


@dataclass(frozen=True)
class ModelConfig:
    """Full model configuration.

    Defaults are calibration placeholders for experiments E1-E6, not empirical
    claims. See docs/model-specification.md for the mechanism formulas.
    """

    seed: int | None = 0
    n_startups: int = 10
    n_anchor_firms: int = 0
    n_universities: int = 0
    n_investors: int = 0
    n_workers: int = 0
    initial_capital: float = 150.0
    burn_rate: float = 1.0
    sectors: tuple[str, ...] = DEFAULT_SECTORS

    infrastructure_capacity: float = 10.0
    funding_conditions: float = 1.0
    labor_market_slack: float = 1.0
    same_sector_compatibility: float = 1.0
    cross_sector_compatibility: float = 0.25
    same_sector_complementarity: float = 0.5
    cross_sector_complementarity: float = 0.5
    policy: Policy = Policy()

    entry_potential_per_period: int = 2
    entry_base_probability: float = 0.05
    entry_reputation_weight: float = 0.3
    entry_funding_weight: float = 0.25
    entry_infrastructure_weight: float = 0.5
    entry_opportunity_weight: float = 0.2
    entry_cost_weight: float = 0.3

    partnership_attempts_per_startup: int = 2
    partnership_base_probability: float = 0.15
    partnership_compatibility_weight: float = 0.3
    partnership_complementarity_weight: float = 0.3
    partnership_reputation_weight: float = 0.2
    partnership_cost_weight: float = 0.25
    partnership_dissolution_probability: float = 0.02
    productive_tie_strength_threshold: float = 0.5

    rnd_share: float = 0.5
    knowledge_rnd_gain: float = 0.3
    market_access_gain: float = 0.1
    knowledge_spillover_rate: float = 0.2
    knowledge_depreciation: float = 0.05
    innovation_event_threshold: float = 0.25

    revenue_per_access: float = 1.0
    labor_cost_per_worker: float = 1.0
    max_team_size: int = 5
    hiring_probability: float = 0.05
    hiring_knowledge_gain: float = 0.3
    investment_probability: float = 0.05
    investment_amount: float = 50.0
    investment_min_quality: float = 0.1
    investor_capital: float = 100.0
    investor_burn_relief: float = 0.25

    congestion_cost_per_org: float = 1.0

    acquisition_probability: float = 0.0
    acquisition_min_quality: float = 0.5
    voluntary_exit_probability: float = 0.0
    migration_probability: float = 0.0

    shock_period: int | None = None
    shock_type: str | None = None
    shock_nodes: int = 1

    anchor_participation: str = "passive"
    anchor_initial_knowledge: float = 5.0
    reputation_update_rate: float = 0.1

    empirical_init: str = "none"
    microdata_path: str = ""
    sector_profiles: str = "none"
    connection_profile: str = "baseline"
    university_participation: str = "passive"
