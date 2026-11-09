"""Mesa-based model of a technology park (phase F2).

Implements the ten-step process order from docs/architecture.md: entry,
environment update, network formation and dissolution, resource allocation,
knowledge diffusion, investment and hiring, finance and congestion, typed
exits, collective reputation, and metrics collection.
"""

from __future__ import annotations

import random
from dataclasses import asdict
from typing import Any, TypedDict

from mesa import Model

from .agents import (
    EXIT_TYPES,
    PARTICIPATION_LEVELS,
    AnchorFirm,
    Investor,
    ParkAuthority,
    Startup,
    University,
    Worker,
)
from .config import SHOCK_TYPES, STREAM_NAMES, ModelConfig, derive_stream_seed
from .empirical import (
    CONNECTION_PROFILES,
    EMPIRICAL_MODES,
    SECTOR_PROFILE_NAMES,
    SECTOR_PROFILES,
    SECTOR_PROXIMITY_WEIGHT,
    UNIVERSITY_COPATENT_BONUS,
    load_microdata,
    sample_anchor_capital,
    sample_anchor_employees,
    sample_research_quality,
    sample_size_class,
    sample_worker,
    sector_proximity,
)
from .environment import Environment
from .metrics import degree_centralization, partnership_density, productive_tie_count
from .network import TypedNetwork

TIE_TYPES: tuple[str, ...] = ("partnership", "investment", "hiring")

ANCHOR_MATCH_BONUS = 0.15


class StepMetrics(TypedDict):
    """Metrics contract v1 step record (docs/adr/0002), extended in F2."""

    period: int
    startup_count: int
    active_startup_count: int
    capital_total: float
    knowledge_total: float
    entry_count: int
    exit_count_by_type: dict[str, int]
    ties_formed_by_type: dict[str, int]
    active_tie_count: int
    partnership_tie_count: int
    productive_tie_count: int
    network_density: float
    degree_centralization: float
    knowledge_mean: float
    innovation_count: int
    innovation_cumulative: int
    quality_mean: float
    employment_total: int
    reputation: float
    congestion: float


def _validate_config(config: ModelConfig) -> None:
    counts = {
        "n_startups": config.n_startups,
        "n_anchor_firms": config.n_anchor_firms,
        "n_universities": config.n_universities,
        "n_investors": config.n_investors,
        "n_workers": config.n_workers,
        "entry_potential_per_period": config.entry_potential_per_period,
        "partnership_attempts_per_startup": config.partnership_attempts_per_startup,
        "max_team_size": config.max_team_size,
    }
    for name, count in counts.items():
        if count < 0:
            raise ValueError(f"{name} must be non-negative")
    if config.seed is not None and not isinstance(config.seed, int):
        raise ValueError("seed must be an integer or None")
    if not config.sectors:
        raise ValueError("at least one sector is required")
    if config.initial_capital < 0:
        raise ValueError("initial_capital must be non-negative")
    if config.burn_rate < 0:
        raise ValueError("burn_rate must be non-negative")
    if config.investor_capital < 0:
        raise ValueError("investor_capital must be non-negative")
    if config.shock_period is not None and config.shock_period < 1:
        raise ValueError("shock_period must be at least 1")
    if config.shock_nodes < 1:
        raise ValueError("shock_nodes must be at least 1")
    if config.shock_type is not None and config.shock_type not in SHOCK_TYPES:
        raise ValueError(f"shock_type must be one of {SHOCK_TYPES}")
    if config.anchor_participation not in PARTICIPATION_LEVELS:
        raise ValueError(f"anchor_participation must be one of {PARTICIPATION_LEVELS}")
    if config.university_participation not in PARTICIPATION_LEVELS:
        raise ValueError(
            f"university_participation must be one of {PARTICIPATION_LEVELS}"
        )
    if config.empirical_init not in EMPIRICAL_MODES:
        raise ValueError(f"empirical_init must be one of {EMPIRICAL_MODES}")
    if config.empirical_init == "microdata" and not config.microdata_path:
        raise ValueError(
            "microdata_path is required when empirical_init is 'microdata'"
        )
    if config.sector_profiles not in SECTOR_PROFILE_NAMES:
        raise ValueError(f"sector_profiles must be one of {SECTOR_PROFILE_NAMES}")
    if config.connection_profile not in CONNECTION_PROFILES:
        raise ValueError(f"connection_profile must be one of {CONNECTION_PROFILES}")

    unit_interval = {
        "rnd_share": config.rnd_share,
        "market_access_gain": config.market_access_gain,
        "knowledge_depreciation": config.knowledge_depreciation,
        "entry_base_probability": config.entry_base_probability,
        "partnership_base_probability": config.partnership_base_probability,
        "partnership_dissolution_probability": (
            config.partnership_dissolution_probability
        ),
        "productive_tie_strength_threshold": (config.productive_tie_strength_threshold),
        "hiring_probability": config.hiring_probability,
        "investment_probability": config.investment_probability,
        "investment_min_quality": config.investment_min_quality,
        "investor_burn_relief": config.investor_burn_relief,
        "acquisition_probability": config.acquisition_probability,
        "acquisition_min_quality": config.acquisition_min_quality,
        "voluntary_exit_probability": config.voluntary_exit_probability,
        "migration_probability": config.migration_probability,
        "reputation_update_rate": config.reputation_update_rate,
    }
    for name, probability in unit_interval.items():
        if not 0.0 <= probability <= 1.0:
            raise ValueError(f"{name} must be in [0, 1]")

    non_negative = {
        "entry_reputation_weight": config.entry_reputation_weight,
        "entry_funding_weight": config.entry_funding_weight,
        "entry_infrastructure_weight": config.entry_infrastructure_weight,
        "entry_opportunity_weight": config.entry_opportunity_weight,
        "entry_cost_weight": config.entry_cost_weight,
        "partnership_compatibility_weight": config.partnership_compatibility_weight,
        "partnership_complementarity_weight": (
            config.partnership_complementarity_weight
        ),
        "partnership_reputation_weight": config.partnership_reputation_weight,
        "partnership_cost_weight": config.partnership_cost_weight,
        "knowledge_rnd_gain": config.knowledge_rnd_gain,
        "knowledge_spillover_rate": config.knowledge_spillover_rate,
        "innovation_event_threshold": config.innovation_event_threshold,
        "revenue_per_access": config.revenue_per_access,
        "labor_cost_per_worker": config.labor_cost_per_worker,
        "hiring_knowledge_gain": config.hiring_knowledge_gain,
        "investment_amount": config.investment_amount,
        "congestion_cost_per_org": config.congestion_cost_per_org,
        "anchor_initial_knowledge": config.anchor_initial_knowledge,
        "investor_capital": config.investor_capital,
    }
    for name, amount in non_negative.items():
        if amount < 0.0:
            raise ValueError(f"{name} must be non-negative")

    policy_unit_interval = {
        "entry_subsidy": config.policy.entry_subsidy,
        "rnd_subsidy": config.policy.rnd_subsidy,
        "shared_infrastructure": config.policy.shared_infrastructure,
        "matchmaking": config.policy.matchmaking,
        "talent_program": config.policy.talent_program,
    }
    for name, probability in policy_unit_interval.items():
        if not 0.0 <= probability <= 1.0:
            raise ValueError(f"policy.{name} must be in [0, 1]")
    if config.policy.investment_fund < 0.0:
        raise ValueError("policy.investment_fund must be non-negative")


class TechnologyParkModel(Model[Any, Any]):
    """Technology park model with deterministic execution under a seed."""

    def __init__(
        self,
        n_startups: int = 10,
        seed: int | None = 0,
        config: ModelConfig | None = None,
    ) -> None:
        if config is None:
            config = ModelConfig(n_startups=n_startups, seed=seed)
        _validate_config(config)
        if config.seed is None:
            super().__init__()
        else:
            super().__init__(rng=config.seed)
        self.config = config
        self.period = 0
        self.environment = Environment.from_config(config)
        self.network = TypedNetwork()
        self.authority = ParkAuthority(self)
        self.startups: list[Startup] = []
        self.anchor_firms: list[AnchorFirm] = []
        self.universities: list[University] = []
        self.investors: list[Investor] = []
        self.workers: list[Worker] = []
        self.streams: dict[str, random.Random] = {}
        seed_value = config.seed
        for name in STREAM_NAMES:
            if seed_value is None:
                self.streams[name] = random.Random()
            else:
                self.streams[name] = random.Random(derive_stream_seed(seed_value, name))
        self.entry_count = 0
        self.exit_counts: dict[str, int] = {exit_type: 0 for exit_type in EXIT_TYPES}
        self.ties_formed: dict[str, int] = {tie_type: 0 for tie_type in TIE_TYPES}
        self.innovation_count = 0
        self.innovation_cumulative = 0
        self._create_population()

    def _create_population(self) -> None:
        config = self.config
        seed_value = config.seed
        attribute_rng = (
            random.Random(derive_stream_seed(seed_value, "empirical"))
            if seed_value is not None
            else random.Random()
        )
        rows: list[dict[str, str]] | None = None
        if config.empirical_init == "microdata":
            rows = load_microdata(config.microdata_path)
        for _ in range(config.n_startups):
            startup = self._add_startup()
            if config.empirical_init != "none":
                startup.size_class = sample_size_class(attribute_rng)
        for index in range(config.n_anchor_firms):
            anchor_attributes: dict[str, Any] = {}
            if config.empirical_init != "none":
                anchor_attributes = {
                    "size_class": "large",
                    "employees": sample_anchor_employees(attribute_rng),
                    "capital": sample_anchor_capital(attribute_rng),
                }
            self.anchor_firms.append(
                AnchorFirm(
                    self,
                    sector=self._sector_for(index),
                    participation=config.anchor_participation,
                    knowledge=config.anchor_initial_knowledge,
                    **anchor_attributes,
                )
            )
        for index in range(config.n_universities):
            research_quality = 0.5
            if config.empirical_init != "none":
                research_quality = sample_research_quality(attribute_rng)
            self.universities.append(
                University(
                    self,
                    sector=self._sector_for(index),
                    research_quality=research_quality,
                )
            )
        for _ in range(config.n_investors):
            self.investors.append(
                Investor(
                    self,
                    capital_available=(
                        self.config.investor_capital
                        + self.environment.policy.investment_fund
                    ),
                )
            )
        for index in range(config.n_workers):
            worker_attributes: dict[str, Any] = {}
            if config.empirical_init != "none":
                worker_attributes = sample_worker(attribute_rng, rows)
            self.workers.append(
                Worker(
                    self,
                    sector=self._sector_for(index),
                    **worker_attributes,
                )
            )

    def _add_startup(self) -> Startup:
        startup = Startup(
            self,
            sector=self._sector_for(len(self.startups)),
            initial_capital=self.config.initial_capital,
        )
        self.startups.append(startup)
        return startup

    def _sector_for(self, index: int) -> str:
        return self.config.sectors[index % len(self.config.sectors)]

    @property
    def active_startups(self) -> list[Startup]:
        return [startup for startup in self.startups if startup.alive]

    def stream(self, name: str) -> random.Random:
        """Return the independent RNG stream for a process."""
        try:
            return self.streams[name]
        except KeyError:
            raise ValueError(f"unknown random stream: {name}") from None

    def step(self) -> None:  # ty: ignore[invalid-method-override]  # Mesa 3.x stub quirk (ADR 0013)
        """Execute one period following the ten-step order in docs/architecture.md."""
        self.entry_count = 0
        self.exit_counts = {exit_type: 0 for exit_type in EXIT_TYPES}
        self.ties_formed = {tie_type: 0 for tie_type in TIE_TYPES}
        self.innovation_count = 0
        self._admit_entrants()
        self._update_environment()
        self._update_network()
        self._apply_shock_if_due()
        knowledge_gains = self._allocate_resources()
        for agent_id, gain in self._diffuse_knowledge().items():
            knowledge_gains[agent_id] = knowledge_gains.get(agent_id, 0.0) + gain
        self._apply_depreciation()
        self._count_innovations(knowledge_gains)
        self.innovation_cumulative += self.innovation_count
        self._execute_investment_and_hiring()
        self._apply_finance_and_congestion()
        self._process_exits()
        self._update_reputation()
        self.period += 1

    def advance(self) -> StepMetrics:
        """Advance one period through the Mesa scheduler and return the record."""
        self.step()  # ty: ignore[missing-argument]  # same Mesa stub quirk as step() above
        return self.metrics()

    def metrics(self) -> StepMetrics:
        """Return the metrics contract v1 step record for the current period."""
        active = self.active_startups
        active_ids = [startup.startup_id for startup in active]
        knowledge_mean = (
            sum(startup.knowledge for startup in active) / len(active)
            if active
            else 0.0
        )
        quality_mean = (
            sum(startup.technology_quality for startup in active) / len(active)
            if active
            else 0.0
        )
        capacity = self._effective_infrastructure_capacity()
        congestion = (
            self.environment.infrastructure_load / capacity if capacity > 0.0 else 0.0
        )
        return {
            "period": self.period,
            "startup_count": len(self.startups),
            "active_startup_count": len(active),
            "capital_total": sum(startup.capital for startup in active),
            "knowledge_total": sum(startup.knowledge for startup in active),
            "entry_count": self.entry_count,
            "exit_count_by_type": dict(self.exit_counts),
            "ties_formed_by_type": dict(self.ties_formed),
            "active_tie_count": self.network.tie_count(),
            "partnership_tie_count": self.network.tie_count("partnership"),
            "productive_tie_count": productive_tie_count(
                self.network, self.config.productive_tie_strength_threshold
            ),
            "network_density": partnership_density(self.network, active_ids),
            "degree_centralization": degree_centralization(self.network, active_ids),
            "knowledge_mean": knowledge_mean,
            "innovation_count": self.innovation_count,
            "innovation_cumulative": self.innovation_cumulative,
            "quality_mean": quality_mean,
            "employment_total": sum(startup.team_size for startup in active),
            "reputation": self.authority.reputation,
            "congestion": congestion,
        }

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the full model state."""
        return {
            "period": self.period,
            "config": asdict(self.config),
            "environment": {
                "sectors": list(self.environment.sector_space.sectors),
                "infrastructure_capacity": self.environment.infrastructure_capacity,
                "infrastructure_load": self.environment.infrastructure_load,
                "funding_conditions": self.environment.funding_conditions,
                "labor_market_slack": self.environment.labor_market_slack,
            },
            "authority": {"reputation": self.authority.reputation},
            "network": [
                {
                    "first": first,
                    "second": second,
                    "tie_type": tie_type,
                    "strength": strength,
                }
                for first, second, tie_type, strength in self.network.entries()
            ],
            "startups": [
                {
                    "id": startup.startup_id,
                    "sector": startup.sector,
                    "capital": startup.capital,
                    "knowledge": startup.knowledge,
                    "technology_quality": startup.technology_quality,
                    "reputation": startup.reputation,
                    "team_size": startup.team_size,
                    "age": startup.age,
                    "access_to_clients": startup.access_to_clients,
                    "access_to_investors": startup.access_to_investors,
                    "alive": startup.alive,
                    "exit_type": startup.exit_type,
                }
                for startup in self.startups
            ],
            "anchor_firms": [
                {
                    "id": anchor.firm_id,
                    "sector": anchor.sector,
                    "capital": anchor.capital,
                    "knowledge": anchor.knowledge,
                    "technology_quality": anchor.technology_quality,
                    "reputation": anchor.reputation,
                    "participation": anchor.participation,
                }
                for anchor in self.anchor_firms
            ],
            "universities": [
                {
                    "id": university.unique_id,
                    "research_quality": university.research_quality,
                    "knowledge_stock": university.knowledge_stock,
                    "technology_transfer_activity": (
                        university.technology_transfer_activity
                    ),
                }
                for university in self.universities
            ],
            "investors": [
                {
                    "id": investor.investor_id,
                    "capital_available": investor.capital_available,
                    "risk_appetite": investor.risk_appetite,
                    "active": investor.active,
                }
                for investor in self.investors
            ],
            "workers": [
                {
                    "id": worker.worker_id,
                    "sector": worker.sector,
                    "skill": worker.skill,
                    "education": worker.education,
                    "age": worker.age,
                    "wage": worker.wage,
                    "employed_by": worker.employed_by,
                }
                for worker in self.workers
            ],
        }

    def _admit_entrants(self) -> None:
        potential = self.config.entry_potential_per_period
        if potential <= 0:
            return
        probability = self._entry_attractiveness()
        rng = self.stream("entry")
        for _ in range(potential):
            sector = self._sector_for(len(self.startups))
            effective = min(
                1.0,
                probability * self._profile_multiplier(sector, "entry"),
            )
            if rng.random() < effective:
                self._add_startup()
                self.entry_count += 1

    def _entry_attractiveness(self) -> float:
        environment = self.environment
        capacity = self._effective_infrastructure_capacity()
        available_infrastructure = (
            max(0.0, 1.0 - environment.infrastructure_load / capacity)
            if capacity > 0.0
            else 0.0
        )
        active = self.active_startups
        opportunity = (
            sum(startup.technology_quality for startup in active) / len(active)
            if active
            else 0.0
        )
        cost_rate = (
            self.config.burn_rate / self.config.initial_capital
            if self.config.initial_capital > 0.0
            else 1.0
        )
        attractiveness = (
            self.config.entry_base_probability
            + self.config.entry_reputation_weight * self.authority.reputation
            + self.config.entry_funding_weight * environment.funding_conditions
            + self.config.entry_infrastructure_weight * available_infrastructure
            + self.config.entry_opportunity_weight * opportunity
            + environment.policy.entry_subsidy
            - self.config.entry_cost_weight * cost_rate
        )
        return min(1.0, max(0.0, attractiveness))

    def _update_environment(self) -> None:
        load = (
            len(self.active_startups) + len(self.anchor_firms) + len(self.universities)
        )
        self.environment.infrastructure_load = float(load)

    def _effective_infrastructure_capacity(self) -> float:
        return self.environment.infrastructure_capacity * (
            1.0 + self.environment.policy.shared_infrastructure
        )

    def _profile_multiplier(self, sector: str, channel: str) -> float:
        if self.config.sector_profiles == "none":
            return 1.0
        profile = SECTOR_PROFILES.get(self.config.sector_profiles, {})
        return float(profile.get(sector, {}).get(channel, 1.0))

    def _congestion_ratio(self) -> float:
        capacity = self._effective_infrastructure_capacity()
        if capacity <= 0.0:
            return 0.0
        return self.environment.infrastructure_load / capacity

    def _network_partners(self) -> dict[int, Startup | AnchorFirm | University]:
        partners: dict[int, Startup | AnchorFirm | University] = {
            startup.startup_id: startup for startup in self.active_startups
        }
        for anchor in self.anchor_firms:
            if anchor.participation == "active":
                partners[anchor.firm_id] = anchor
        if self.config.university_participation == "active":
            for university in self.universities:
                partners[university.university_id] = university
        return partners

    def _update_network(self) -> None:
        self._dissolve_partnerships()
        self._form_partnerships()

    def _dissolve_partnerships(self) -> None:
        probability = self.config.partnership_dissolution_probability
        if probability <= 0.0:
            return
        rng = self.stream("partnerships")
        for first_id, second_id, _strength in list(self.network.pairs("partnership")):
            if rng.random() < probability:
                self.network.remove_tie(first_id, second_id, "partnership")

    def _form_partnerships(self) -> None:
        attempts = self.config.partnership_attempts_per_startup
        if attempts <= 0:
            return
        partners = self._network_partners()
        if len(partners) < 2:
            return
        partner_list = list(partners.values())
        rng = self.stream("partnerships")
        for startup in self.active_startups:
            for _ in range(attempts):
                other = rng.choice(partner_list)
                if other is startup:
                    continue
                other_id = self._partner_id(other)
                if self.network.has_tie(startup.startup_id, other_id, "partnership"):
                    continue
                if rng.random() < self._partnership_probability(startup, other):
                    strength = self._tie_strength(startup, other)
                    self.network.add_tie(
                        startup.startup_id,
                        other_id,
                        "partnership",
                        strength,
                    )
                    self.ties_formed["partnership"] += 1

    def _partnership_probability(
        self,
        first: Startup | AnchorFirm | University,
        second: Startup | AnchorFirm | University,
    ) -> float:
        sector_space = self.environment.sector_space
        compatibility = sector_space.compatibility(first.sector, second.sector)
        complementarity = sector_space.complementarity(first.sector, second.sector)
        mean_reputation = (first.reputation + second.reputation) / 2.0
        probability = (
            self.config.partnership_base_probability
            + self.config.partnership_compatibility_weight * compatibility
            + self.config.partnership_complementarity_weight * complementarity
            + self.config.partnership_reputation_weight * mean_reputation
            + self.environment.policy.matchmaking
            - self.config.partnership_cost_weight * min(1.0, self._congestion_ratio())
        )
        if self.config.connection_profile == "empirical":
            first_is_anchor = isinstance(first, AnchorFirm)
            second_is_anchor = isinstance(second, AnchorFirm)
            if first_is_anchor != second_is_anchor:
                probability += ANCHOR_MATCH_BONUS
            probability += (
                sector_proximity(first.sector, second.sector) * SECTOR_PROXIMITY_WEIGHT
            )
            university_anchor = (
                isinstance(first, University) and isinstance(second, AnchorFirm)
            ) or (isinstance(first, AnchorFirm) and isinstance(second, University))
            if university_anchor:
                probability += UNIVERSITY_COPATENT_BONUS
        return min(1.0, max(0.0, probability))

    def _tie_strength(
        self,
        first: Startup | AnchorFirm | University,
        second: Startup | AnchorFirm | University,
    ) -> float:
        sector_space = self.environment.sector_space
        compatibility = sector_space.compatibility(first.sector, second.sector)
        complementarity = sector_space.complementarity(first.sector, second.sector)
        return (compatibility + complementarity) / 2.0

    @staticmethod
    def _partner_id(agent: Startup | AnchorFirm | University) -> int:
        if isinstance(agent, Startup):
            return agent.startup_id
        if isinstance(agent, University):
            return agent.university_id
        return agent.firm_id

    def _allocate_resources(self) -> dict[int, float]:
        gains: dict[int, float] = {}
        rnd_effort = self.config.rnd_share
        for startup in self.active_startups:
            gain = (
                self.config.knowledge_rnd_gain
                * rnd_effort
                * (1.0 + self.environment.policy.rnd_subsidy)
            )
            startup.knowledge += gain
            startup.access_to_clients = min(
                1.0,
                startup.access_to_clients
                + self.config.market_access_gain * (1.0 - rnd_effort),
            )
            gains[startup.startup_id] = gain
        return gains

    def _diffuse_knowledge(self) -> dict[int, float]:
        gains: dict[int, float] = {}
        rate = self.config.knowledge_spillover_rate
        if rate <= 0.0:
            return gains
        partners = self._network_partners()
        for first_id, second_id, strength in self.network.pairs("partnership"):
            first = partners.get(first_id)
            second = partners.get(second_id)
            if first is None or second is None:
                continue
            if first.knowledge < second.knowledge:
                learner_id: int = first_id
                learner: Startup | AnchorFirm | University = first
                source: Startup | AnchorFirm | University = second
            else:
                learner_id = second_id
                learner = second
                source = first
            gain = rate * strength * (source.knowledge - learner.knowledge)
            if gain > 0.0:
                gains[learner_id] = gains.get(learner_id, 0.0) + gain
        for agent_id, gain in gains.items():
            partners[agent_id].knowledge += gain
        self._refresh_quality()
        return gains

    def _apply_depreciation(self) -> None:
        depreciation = self.config.knowledge_depreciation
        if depreciation <= 0.0:
            return
        agents: list[Startup | AnchorFirm | University] = [
            *self.active_startups,
            *self.anchor_firms,
            *self.universities,
        ]
        for agent in agents:
            agent.knowledge *= 1.0 - depreciation

    def _refresh_quality(self) -> None:
        agents: list[Startup | AnchorFirm | University] = [
            *self.active_startups,
            *self.anchor_firms,
            *self.universities,
        ]
        for agent in agents:
            agent.technology_quality = agent.knowledge / (1.0 + agent.knowledge)
            agent.reputation = agent.technology_quality

    def _count_innovations(self, gains: dict[int, float]) -> None:
        threshold = self.config.innovation_event_threshold
        startup_ids = {startup.startup_id for startup in self.active_startups}
        self.innovation_count = sum(
            1
            for agent_id, gain in gains.items()
            if agent_id in startup_ids and gain >= threshold
        )

    def _execute_investment_and_hiring(self) -> None:
        rng = self.stream("finance")
        self._execute_investments(rng)
        self._execute_hiring(rng)
        self._refresh_quality()

    def _execute_investments(self, rng: random.Random) -> None:
        amount = self.config.investment_amount
        if amount <= 0.0:
            return
        for investor in self.investors:
            if not investor.active or investor.capital_available < amount:
                continue
            candidates = [
                startup
                for startup in self.active_startups
                if startup.technology_quality >= self.config.investment_min_quality
            ]
            if not candidates:
                continue
            if rng.random() >= self.config.investment_probability:
                continue
            if self.config.connection_profile == "empirical":
                target = max(
                    candidates,
                    key=lambda item: (item.technology_quality, -item.startup_id),
                )
            else:
                target = rng.choice(candidates)
            investor.capital_available -= amount
            target.capital += amount
            target.access_to_investors = 1.0
            self.network.add_tie(
                investor.investor_id,
                target.startup_id,
                "investment",
            )
            self.ties_formed["investment"] += 1

    def _execute_hiring(self, rng: random.Random) -> None:
        if self.config.hiring_probability <= 0.0:
            return
        unemployed = [worker for worker in self.workers if worker.employed_by is None]
        for startup in self.active_startups:
            if not unemployed:
                break
            if startup.team_size >= self.config.max_team_size:
                continue
            effective = min(
                1.0,
                self.config.hiring_probability
                * self._profile_multiplier(startup.sector, "hiring"),
            )
            if rng.random() >= effective:
                continue
            if self.config.connection_profile == "empirical":
                worker = max(unemployed, key=lambda item: (item.skill, -item.worker_id))
                unemployed.remove(worker)
            else:
                worker = unemployed.pop(0)
            worker.employed_by = startup.startup_id
            startup.team_size += 1
            startup.knowledge += (
                self.config.hiring_knowledge_gain
                * (1.0 + self.environment.policy.talent_program)
                * worker.skill
            )
            self.network.add_tie(worker.worker_id, startup.startup_id, "hiring")
            self.ties_formed["hiring"] += 1

    def _apply_finance_and_congestion(self) -> None:
        environment = self.environment
        excess = max(
            0.0,
            environment.infrastructure_load - self._effective_infrastructure_capacity(),
        )
        congestion_cost = self.config.congestion_cost_per_org * excess
        relief = self.config.investor_burn_relief
        for startup in self.active_startups:
            startup.age += 1
            revenue = (
                self.config.revenue_per_access
                * startup.technology_quality
                * startup.access_to_clients
            )
            startup.capital += revenue
            burn = self.config.burn_rate
            if startup.access_to_investors >= 1.0:
                burn *= 1.0 - relief
            labor_cost = self.config.labor_cost_per_worker * (startup.team_size - 1)
            startup.capital = max(
                0.0, startup.capital - burn - labor_cost - congestion_cost
            )

    def _process_exits(self) -> None:
        rng = self.stream("exit")
        for startup in list(self.startups):
            if not startup.alive:
                continue
            if startup.capital <= 0.0:
                self._exit_startup(startup, "failure")
                continue
            if (
                self.anchor_firms
                and startup.technology_quality >= self.config.acquisition_min_quality
                and rng.random() < self.config.acquisition_probability
            ):
                self._exit_startup(startup, "acquisition")
                continue
            exit_multiplier = self._profile_multiplier(startup.sector, "exit")
            if rng.random() < min(
                1.0,
                self.config.voluntary_exit_probability * exit_multiplier,
            ):
                self._exit_startup(startup, "voluntary")
                continue
            if rng.random() < min(
                1.0,
                self.config.migration_probability * exit_multiplier,
            ):
                self._exit_startup(startup, "migration")

    def _exit_startup(self, startup: Startup, exit_type: str) -> None:
        startup.exit(exit_type)
        self.exit_counts[exit_type] += 1
        self.network.remove_agent(startup.startup_id)
        # Layoff: workers employed by the exiting startup return to the
        # unemployed pool (employed_by = None) so surviving startups can
        # rehire them from the next period on. Without this, a worker whose
        # employer exited kept a stale employed_by pointing at a dead startup
        # and was never rehired.
        for worker in self.workers:
            if worker.employed_by == startup.startup_id:
                worker.employed_by = None

    def _apply_shock_if_due(self) -> None:
        if self.config.shock_period is None:
            return
        if self.period + 1 != self.config.shock_period:
            return
        if self.config.shock_type == "central_firm":
            self._collapse_central_startup()
        elif self.config.shock_type == "funding":
            self._collapse_funding()

    def _collapse_central_startup(self) -> None:
        active = self.active_startups
        if not active:
            return
        present = {startup.startup_id for startup in active}
        degrees = {startup.startup_id: 0 for startup in active}
        for first, second, _strength in self.network.pairs("partnership"):
            if first in present and second in present:
                degrees[first] += 1
                degrees[second] += 1
        ranked = sorted(degrees, key=lambda agent_id: (-degrees[agent_id], agent_id))
        collapsed = set(ranked[: self.config.shock_nodes])
        for startup in active:
            if startup.startup_id in collapsed:
                startup.capital = 0.0

    def _collapse_funding(self) -> None:
        for investor in self.investors:
            investor.active = False
            investor.capital_available = 0.0
        for startup in self.active_startups:
            startup.access_to_investors = 0.0

    def _update_reputation(self) -> None:
        started = len(self.startups)
        target = len(self.active_startups) / started if started > 0 else 0.0
        rate = self.config.reputation_update_rate
        reputation = self.authority.reputation + rate * (
            target - self.authority.reputation
        )
        self.authority.reputation = min(1.0, max(0.0, reputation))


def run_demo() -> None:
    """Print a short deterministic demonstration run."""
    model = TechnologyParkModel(n_startups=3, seed=42)
    for _ in range(3):
        print(model.advance())


if __name__ == "__main__":
    run_demo()
