"""Sector profiles, connection profile, and university participation."""

from __future__ import annotations

from dataclasses import replace

from technology_park_abm import ModelConfig, TechnologyParkModel


def test_sector_profiles_shift_entry_by_sector() -> None:
    software = ModelConfig(
        seed=3,
        sectors=("software",),
        entry_potential_per_period=40,
        entry_base_probability=0.5,
        entry_reputation_weight=0.0,
        entry_funding_weight=0.0,
        entry_infrastructure_weight=0.0,
        entry_opportunity_weight=0.0,
        entry_cost_weight=0.0,
        sector_profiles="brazil_tech",
    )
    hardware = replace(software, sectors=("hardware",))
    software_model = TechnologyParkModel(config=software)
    hardware_model = TechnologyParkModel(config=hardware)
    for _ in range(5):
        software_model.advance()
        hardware_model.advance()
    assert len(software_model.startups) > len(hardware_model.startups)


def test_sector_profiles_shift_voluntary_exits_by_sector() -> None:
    base = ModelConfig(
        seed=4,
        sectors=("software",),
        n_startups=30,
        entry_potential_per_period=0,
        voluntary_exit_probability=0.3,
        rnd_share=0.0,
        sector_profiles="brazil_tech",
    )
    hardware = replace(base, sectors=("hardware",))
    software_exits = TechnologyParkModel(config=base).advance()["exit_count_by_type"][
        "voluntary"
    ]
    hardware_exits = TechnologyParkModel(config=hardware).advance()[
        "exit_count_by_type"
    ]["voluntary"]
    assert hardware_exits >= software_exits
    assert hardware_exits > 0


def test_connection_profile_adds_anchor_match_bonus() -> None:
    baseline = ModelConfig(
        seed=1,
        n_startups=2,
        n_anchor_firms=1,
        anchor_participation="active",
    )
    baseline_model = TechnologyParkModel(config=baseline)
    empirical_model = TechnologyParkModel(
        config=replace(baseline, connection_profile="empirical")
    )
    base_probability = baseline_model._partnership_probability(
        baseline_model.startups[0], baseline_model.anchor_firms[0]
    )
    empirical_probability = empirical_model._partnership_probability(
        empirical_model.startups[0], empirical_model.anchor_firms[0]
    )
    assert empirical_probability >= base_probability + 0.14


def test_connection_profile_hires_most_skilled_first() -> None:
    config = ModelConfig(
        seed=2,
        n_startups=1,
        n_workers=2,
        entry_potential_per_period=0,
        hiring_probability=1.0,
        connection_profile="empirical",
    )
    model = TechnologyParkModel(config=config)
    model.workers[0].skill = 0.2
    model.workers[1].skill = 0.9
    model.advance()
    employed = [worker for worker in model.workers if worker.employed_by is not None]
    assert len(employed) == 1
    assert employed[0].skill == 0.9


def test_connection_profile_adds_sector_proximity_bonus() -> None:
    baseline = ModelConfig(
        seed=8,
        n_startups=2,
        sectors=("software",),
        entry_potential_per_period=0,
    )
    baseline_model = TechnologyParkModel(config=baseline)
    empirical_model = TechnologyParkModel(
        config=replace(baseline, connection_profile="empirical")
    )
    base_probability = baseline_model._partnership_probability(
        baseline_model.startups[0], baseline_model.startups[1]
    )
    empirical_probability = empirical_model._partnership_probability(
        empirical_model.startups[0], empirical_model.startups[1]
    )
    assert empirical_probability >= base_probability + 0.09


def test_connection_profile_adds_university_copatent_bonus() -> None:
    baseline = ModelConfig(
        seed=9,
        n_startups=0,
        sectors=("software",),
        n_universities=1,
        n_anchor_firms=1,
        anchor_participation="active",
        university_participation="active",
        entry_potential_per_period=0,
    )
    baseline_model = TechnologyParkModel(config=baseline)
    empirical_model = TechnologyParkModel(
        config=replace(baseline, connection_profile="empirical")
    )
    university = baseline_model.universities[0]
    anchor = baseline_model.anchor_firms[0]
    base_probability = baseline_model._partnership_probability(university, anchor)
    empirical_probability = empirical_model._partnership_probability(
        empirical_model.universities[0], empirical_model.anchor_firms[0]
    )
    assert empirical_probability >= base_probability + 0.19


def test_active_university_forms_ties() -> None:
    base = ModelConfig(
        seed=6,
        n_startups=4,
        n_universities=1,
        entry_potential_per_period=0,
        partnership_attempts_per_startup=3,
        partnership_base_probability=0.5,
        partnership_dissolution_probability=0.0,
    )
    active = TechnologyParkModel(
        config=replace(base, university_participation="active")
    )
    passive = TechnologyParkModel(config=base)
    university_id = active.universities[0].university_id
    for _ in range(10):
        active.advance()
        passive.advance()
    assert [tie for tie in active.network.entries() if university_id in tie[:2]]
    passive_id = passive.universities[0].university_id
    assert not [tie for tie in passive.network.entries() if passive_id in tie[:2]]
