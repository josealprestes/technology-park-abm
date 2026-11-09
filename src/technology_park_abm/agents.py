"""Agent state definitions for the technology park.

Agents expose explicit state variables. Processes that change this state are
orchestrated by the model in the ten-step order documented in
docs/architecture.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mesa import Agent

from .empirical import EDUCATION_LEVELS

if TYPE_CHECKING:
    from .model import TechnologyParkModel

PARTICIPATION_LEVELS: tuple[str, ...] = ("passive", "active")

EXIT_TYPES: tuple[str, ...] = ("failure", "acquisition", "voluntary", "migration")


class Startup(Agent["TechnologyParkModel"]):
    """A park startup with explicit state per the model specification."""

    def __init__(
        self,
        model: TechnologyParkModel,
        *,
        sector: str,
        initial_capital: float = 100.0,
        size_class: str = "micro",
    ) -> None:
        super().__init__(model)
        if initial_capital < 0:
            raise ValueError("initial_capital must be non-negative")
        self.sector = sector
        self.size_class = size_class
        self.capital = initial_capital
        self.technology_quality = 0.0
        self.knowledge = 0.0
        self.reputation = 0.0
        self.team_size = 1
        self.age = 0
        self.access_to_clients = 0.0
        self.access_to_investors = 0.0
        self.alive = True
        self.exit_type: str | None = None

    @property
    def startup_id(self) -> int:
        assert self.unique_id is not None
        return int(self.unique_id)

    @property
    def can_act(self) -> bool:
        """Dead agents cannot create new ties or outputs."""
        return self.alive

    def exit(self, exit_type: str) -> None:
        """Mark the startup as exited with a distinguishable type."""
        if exit_type not in EXIT_TYPES:
            raise ValueError(f"exit_type must be one of {EXIT_TYPES}")
        if not self.alive:
            return
        self.alive = False
        self.exit_type = exit_type
        if exit_type == "failure":
            self.capital = 0.0

    def step(self, burn_rate: float = 1.0) -> None:
        """Accrue one period of operating cost and exit on failure."""
        if not self.alive:
            return
        self.age += 1
        self.capital -= burn_rate
        if self.capital <= 0.0:
            self.exit("failure")


class AnchorFirm(Agent["TechnologyParkModel"]):
    """A large established firm whose network participation is an E3 lever."""

    def __init__(
        self,
        model: TechnologyParkModel,
        *,
        sector: str,
        capital: float = 1000.0,
        participation: str = "passive",
        knowledge: float = 0.0,
        size_class: str = "large",
        employees: int = 500,
    ) -> None:
        super().__init__(model)
        if participation not in PARTICIPATION_LEVELS:
            raise ValueError(f"participation must be one of {PARTICIPATION_LEVELS}")
        if capital < 0:
            raise ValueError("capital must be non-negative")
        if knowledge < 0:
            raise ValueError("knowledge must be non-negative")
        if employees < 0:
            raise ValueError("employees must be non-negative")
        self.sector = sector
        self.size_class = size_class
        self.employees = employees
        self.capital = capital
        self.knowledge = knowledge
        self.technology_quality = knowledge / (1.0 + knowledge)
        self.reputation = 0.0
        self.participation = participation

    @property
    def firm_id(self) -> int:
        assert self.unique_id is not None
        return int(self.unique_id)

    @property
    def can_act(self) -> bool:
        return True


class University(Agent["TechnologyParkModel"]):
    """University or ICT performing research and technology transfer."""

    def __init__(
        self,
        model: TechnologyParkModel,
        *,
        sector: str = "research",
        research_quality: float = 0.5,
        knowledge_stock: float = 0.0,
    ) -> None:
        super().__init__(model)
        if not 0.0 <= research_quality <= 1.0:
            raise ValueError("research_quality must be in [0, 1]")
        if knowledge_stock < 0:
            raise ValueError("knowledge_stock must be non-negative")
        self.sector = sector
        self.research_quality = research_quality
        self.knowledge = knowledge_stock
        self.technology_quality = knowledge_stock / (1.0 + knowledge_stock)
        self.reputation = 0.0
        self.technology_transfer_activity = 0.0

    @property
    def university_id(self) -> int:
        assert self.unique_id is not None
        return int(self.unique_id)

    @property
    def knowledge_stock(self) -> float:
        return self.knowledge


class Investor(Agent["TechnologyParkModel"]):
    """Investor with available capital and risk appetite."""

    def __init__(
        self,
        model: TechnologyParkModel,
        *,
        capital_available: float = 100.0,
        risk_appetite: float = 0.5,
    ) -> None:
        super().__init__(model)
        if capital_available < 0:
            raise ValueError("capital_available must be non-negative")
        if not 0.0 <= risk_appetite <= 1.0:
            raise ValueError("risk_appetite must be in [0, 1]")
        self.capital_available = capital_available
        self.risk_appetite = risk_appetite
        self.active = True

    @property
    def investor_id(self) -> int:
        assert self.unique_id is not None
        return int(self.unique_id)


class Worker(Agent["TechnologyParkModel"]):
    """Qualified worker in the park labor market."""

    def __init__(
        self,
        model: TechnologyParkModel,
        *,
        sector: str | None = None,
        skill: float = 0.5,
        education: str = "medio",
        age: int = 30,
        wage: float = 2.0,
    ) -> None:
        super().__init__(model)
        if not 0.0 <= skill <= 1.0:
            raise ValueError("skill must be in [0, 1]")
        if education not in EDUCATION_LEVELS:
            raise ValueError(f"education must be one of {EDUCATION_LEVELS}")
        if age < 0:
            raise ValueError("age must be non-negative")
        if wage < 0:
            raise ValueError("wage must be non-negative")
        self.sector = sector
        self.skill = skill
        self.education = education
        self.age = age
        self.wage = wage
        self.employed_by: int | None = None

    @property
    def worker_id(self) -> int:
        assert self.unique_id is not None
        return int(self.unique_id)


class ParkAuthority(Agent["TechnologyParkModel"]):
    """Park governance holding policy and collective reputation state."""

    def __init__(self, model: TechnologyParkModel) -> None:
        super().__init__(model)
        self.policy = model.environment.policy
        self.reputation = 0.0
