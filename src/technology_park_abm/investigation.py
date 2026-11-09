"""Opt-in UI adapter: real seeded trajectories, events and network frames.

This module does not change model defaults or mechanisms. It also serves the
offline prototype builder so cached and newly requested runs share one path.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import CancelledError
from dataclasses import asdict
from threading import Event
from typing import Any

from .model import TechnologyParkModel
from .workbench_core import MapSession, config_from_params

METRICS = (
    "active_startup_count",
    "productive_tie_count",
    "knowledge_mean",
    "innovation_cumulative",
    "capital_total",
    "congestion",
)
MAX_PERIODS = 80
MAX_SEEDS = 8


def validate_investigation(
    params: Mapping[str, Any], seeds: Sequence[int], periods: int
) -> None:
    """Keep interactive jobs finite; scientific validation stays canonical."""
    if not seeds or len(seeds) > MAX_SEEDS or len(set(seeds)) != len(seeds):
        raise ValueError("Escolha de 1 a 8 sementes distintas.")
    if any(type(seed) is not int or not 0 <= seed <= 1_000_007 for seed in seeds):
        raise ValueError("As sementes devem ser inteiros entre 0 e 1.000.007.")
    if type(periods) is not int or not 1 <= periods <= MAX_PERIODS:
        raise ValueError("Escolha de 1 a 80 períodos.")
    for value in params.values():
        if isinstance(value, (int, float)) and not math.isfinite(value):
            raise ValueError("Os parâmetros numéricos precisam ser finitos.")
    if params.get("empirical_init") == "microdata" or params.get("microdata_path"):
        raise ValueError("Nesta interface, use dados sintéticos ou agregados públicos.")
    config = config_from_params({**params, "seed": seeds[0]})
    configured = asdict(config)
    policy = configured.pop("policy")
    if any(
        isinstance(value, (int, float)) and not math.isfinite(value)
        for value in (*configured.values(), *policy.values())
    ):
        raise ValueError("Os parâmetros numéricos precisam ser finitos.")
    if any(
        isinstance(value, (int, float)) and abs(value) > 1_000_000_000
        for value in (*configured.values(), *policy.values())
    ):
        raise ValueError("Nesta interface, use valores numéricos de até um bilhão.")
    if len(config.sectors) > 12 or any(len(name) > 40 for name in config.sectors):
        raise ValueError("Use até 12 setores, com até 40 caracteres por nome.")
    if config.partnership_attempts_per_startup > 20:
        raise ValueError("Use até 20 tentativas de parceria por startup e período.")
    populations = (
        config.n_startups,
        config.n_anchor_firms,
        config.n_universities,
        config.n_investors,
        config.n_workers,
    )
    if max(populations) > 100 or sum(populations) > 150:
        raise ValueError(
            "Use até 100 agentes por tipo e 150 agentes iniciais no total."
        )
    if config.entry_potential_per_period > 5:
        raise ValueError("Nesta interface, use até 5 entradas potenciais por período.")


def run_scenario(
    params: dict[str, Any],
    seeds: Sequence[int],
    periods: int = MAX_PERIODS,
    *,
    cancel: Event | None = None,
    progress: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Record every period; network frames use the explicitly labeled first seed."""
    validate_investigation(params, seeds, periods)
    runs: list[dict[str, Any]] = []
    maps: dict[str, Any] = {}
    labels = {"startup": "S", "anchor": "A", "university": "U"}
    labels.update({"investor": "I", "worker": "T"})

    def checkpoint() -> None:
        if cancel is not None and cancel.is_set():
            raise CancelledError("Execução cancelada.")

    for index, seed in enumerate(seeds):
        checkpoint()
        seeded_params = {**params, "seed": seed}
        model = TechnologyParkModel(config=config_from_params(seeded_params))
        initial = dict(model.metrics())
        history: list[dict[str, Any]] = []
        for _ in range(periods):
            checkpoint()
            record: dict[str, Any] = dict(model.advance())
            if int(record["active_tie_count"]) > 3_000:
                raise ValueError(
                    "A rede ultrapassou 3.000 relações. Reduza sua configuração."
                )
            if not all(math.isfinite(float(record[key])) for key in METRICS):
                raise ValueError(
                    "Resultado não finito. Reduza os valores da configuração."
                )
            history.append(record)
        if seed == seeds[0]:
            session = MapSession(seeded_params)
            for period in range(periods + 1):
                if period:
                    session.step(1)
                state = session.state()
                maps[str(period)] = {
                    key: state[key]
                    for key in ("period", "nodes", "edges", "positions", "regions")
                }
                for node in maps[str(period)]["nodes"]:
                    node["label"] = f"{labels[node['type']]}{node['id']}"
                    if node["type"] == "university":
                        node["participation"] = model.config.university_participation
        runs.append(
            {
                "seed": seed,
                "initial": {key: initial[key] for key in ("period", *METRICS)},
                "history": [
                    {key: record[key] for key in ("period", *METRICS)}
                    for record in history
                ],
                "events": [
                    {
                        key: record[key]
                        for key in (
                            "period",
                            "entry_count",
                            "exit_count_by_type",
                            "ties_formed_by_type",
                            "innovation_count",
                            "employment_total",
                        )
                    }
                    for record in history
                ],
            }
        )
        if progress is not None:
            progress(index + 1)
    return {
        "capacity": config_from_params(params).infrastructure_capacity,
        "config": asdict(config_from_params({**params, "seed": seeds[0]})),
        "runs": runs,
        "maps": maps,
    }
