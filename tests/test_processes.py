from dataclasses import replace

from technology_park_abm import ModelConfig, TechnologyParkModel

QUIET_CONFIG = ModelConfig(
    n_startups=0,
    seed=0,
    initial_capital=100.0,
    entry_potential_per_period=0,
    partnership_attempts_per_startup=0,
    partnership_dissolution_probability=0.0,
    rnd_share=0.0,
    market_access_gain=0.0,
    knowledge_spillover_rate=0.0,
    knowledge_depreciation=0.0,
)


def test_entry_disabled_when_potential_is_zero() -> None:
    model = TechnologyParkModel(config=QUIET_CONFIG)
    for _ in range(5):
        record = model.advance()
    assert record["entry_count"] == 0
    assert record["startup_count"] == 0


def test_entry_adds_potential_entrants() -> None:
    config = replace(
        QUIET_CONFIG,
        entry_potential_per_period=2,
        entry_base_probability=1.0,
    )
    record = TechnologyParkModel(config=config).advance()
    assert record["entry_count"] == 2
    assert record["startup_count"] == 2


def test_reputation_increases_entry() -> None:
    config = replace(
        QUIET_CONFIG,
        entry_potential_per_period=10,
        entry_base_probability=0.0,
        entry_reputation_weight=1.0,
        entry_funding_weight=0.0,
        entry_infrastructure_weight=0.0,
        entry_opportunity_weight=0.0,
        entry_cost_weight=0.0,
    )
    high = TechnologyParkModel(config=config)
    low = TechnologyParkModel(config=config)
    high.authority.reputation = 1.0
    low.authority.reputation = 0.0
    assert high.advance()["entry_count"] == 10
    assert low.advance()["entry_count"] == 0


def test_compatibility_increases_partnership_ties() -> None:
    base = replace(
        QUIET_CONFIG,
        n_startups=4,
        partnership_attempts_per_startup=3,
        partnership_base_probability=0.0,
        partnership_compatibility_weight=1.0,
        partnership_complementarity_weight=0.0,
        partnership_reputation_weight=0.0,
        partnership_cost_weight=0.0,
    )
    high = TechnologyParkModel(config=replace(base, sectors=("alpha",)))
    low = TechnologyParkModel(config=replace(base, sectors=("alpha", "beta")))
    high_record = high.advance()
    low_record = low.advance()
    assert high_record["partnership_tie_count"] > low_record["partnership_tie_count"]


def test_active_anchor_forms_partnerships() -> None:
    base = replace(
        QUIET_CONFIG,
        n_startups=2,
        n_anchor_firms=1,
        partnership_attempts_per_startup=5,
        partnership_base_probability=1.0,
    )
    active = TechnologyParkModel(config=replace(base, anchor_participation="active"))
    passive = TechnologyParkModel(config=base)
    active_record = active.advance()
    passive_record = passive.advance()
    anchor_id = active.anchor_firms[0].firm_id
    assert active_record["partnership_tie_count"] >= 1
    assert any(anchor_id in pair[:2] for pair in active.network.pairs())
    passive_anchor_id = passive.anchor_firms[0].firm_id
    assert not any(passive_anchor_id in pair[:2] for pair in passive.network.pairs())
    assert passive_record["partnership_tie_count"] >= 1


def test_knowledge_diffuses_through_partnership_ties() -> None:
    config = replace(QUIET_CONFIG, n_startups=2, knowledge_spillover_rate=0.5)
    model = TechnologyParkModel(config=config)
    first, second = model.startups
    first.knowledge = 0.0
    second.knowledge = 10.0
    model.network.add_tie(first.startup_id, second.startup_id, "partnership", 1.0)
    record = model.advance()
    assert first.knowledge == 5.0
    assert second.knowledge == 10.0
    assert record["innovation_count"] == 1


def test_diffusion_is_separable_from_other_mechanisms() -> None:
    model = TechnologyParkModel(config=replace(QUIET_CONFIG, n_startups=2))
    first, second = model.startups
    first.knowledge = 0.0
    second.knowledge = 10.0
    model.network.add_tie(first.startup_id, second.startup_id, "partnership", 1.0)
    model.advance()
    assert first.knowledge == 0.0
    assert second.knowledge == 10.0


def test_depreciation_reduces_knowledge() -> None:
    config = replace(QUIET_CONFIG, n_startups=1, knowledge_depreciation=0.5)
    model = TechnologyParkModel(config=config)
    model.startups[0].knowledge = 10.0
    model.advance()
    assert model.startups[0].knowledge == 5.0


def test_innovation_events_count_large_gains() -> None:
    config = replace(
        QUIET_CONFIG,
        n_startups=3,
        rnd_share=1.0,
        knowledge_rnd_gain=1.0,
        innovation_event_threshold=0.5,
    )
    record = TechnologyParkModel(config=config).advance()
    assert record["innovation_count"] == 3


def test_congestion_raises_costs() -> None:
    congested = replace(
        QUIET_CONFIG,
        n_startups=5,
        infrastructure_capacity=1.0,
        congestion_cost_per_org=2.0,
    )
    roomy = replace(congested, infrastructure_capacity=1000.0)
    congested_record = TechnologyParkModel(config=congested).advance()
    roomy_record = TechnologyParkModel(config=roomy).advance()
    assert congested_record["capital_total"] == 455.0
    assert roomy_record["capital_total"] == 495.0
    assert congested_record["congestion"] == 5.0


def test_investment_transfers_capital_and_creates_tie() -> None:
    config = replace(
        QUIET_CONFIG,
        n_startups=1,
        n_investors=1,
        investment_probability=1.0,
        investment_min_quality=0.0,
    )
    model = TechnologyParkModel(config=config)
    record = model.advance()
    startup = model.startups[0]
    investor = model.investors[0]
    # V2-4: funded startups burn (1 - relief); 100 + 50 - 0.75 = 149.25.
    assert startup.capital == 149.25
    assert startup.access_to_investors == 1.0
    assert investor.capital_available == 50.0
    assert record["active_tie_count"] == 1
    assert model.network.tie_count("investment") == 1


def test_hiring_employs_worker_and_adds_knowledge() -> None:
    config = replace(
        QUIET_CONFIG,
        n_startups=1,
        n_workers=1,
        hiring_probability=1.0,
    )
    model = TechnologyParkModel(config=config)
    record = model.advance()
    startup = model.startups[0]
    worker = model.workers[0]
    assert startup.team_size == 2
    assert startup.knowledge == 0.15
    assert worker.employed_by == startup.startup_id
    assert record["employment_total"] == 2
    assert model.network.tie_count("hiring") == 1


def test_voluntary_exit_is_distinguishable() -> None:
    config = replace(QUIET_CONFIG, n_startups=1, voluntary_exit_probability=1.0)
    record = TechnologyParkModel(config=config).advance()
    assert record["exit_count_by_type"]["voluntary"] == 1
    assert record["active_startup_count"] == 0


def test_migration_exit_is_distinguishable() -> None:
    config = replace(QUIET_CONFIG, n_startups=1, migration_probability=1.0)
    record = TechnologyParkModel(config=config).advance()
    assert record["exit_count_by_type"]["migration"] == 1


def test_acquisition_requires_anchor() -> None:
    with_anchor = replace(
        QUIET_CONFIG,
        n_startups=1,
        n_anchor_firms=1,
        acquisition_probability=1.0,
        acquisition_min_quality=0.0,
    )
    without_anchor = replace(with_anchor, n_anchor_firms=0)
    with_record = TechnologyParkModel(config=with_anchor).advance()
    without_record = TechnologyParkModel(config=without_anchor).advance()
    assert with_record["exit_count_by_type"]["acquisition"] == 1
    assert without_record["exit_count_by_type"]["acquisition"] == 0


def test_failure_exit_is_distinguishable() -> None:
    config = replace(QUIET_CONFIG, n_startups=1, initial_capital=1.0, burn_rate=2.0)
    record = TechnologyParkModel(config=config).advance()
    assert record["exit_count_by_type"]["failure"] == 1
    assert record["capital_total"] == 0.0


def test_exit_removes_incident_ties() -> None:
    model = TechnologyParkModel(config=replace(QUIET_CONFIG, n_startups=2))
    first, second = model.startups
    second.capital = 1.0
    model.network.add_tie(first.startup_id, second.startup_id, "partnership", 1.0)
    record = model.advance()
    assert record["exit_count_by_type"]["failure"] == 1
    assert model.network.tie_count() == 0


def test_exit_lays_off_workers_back_to_unemployed_pool() -> None:
    # Layoff fix: when a startup exits, its workers' employed_by is reset to
    # None (they return to the unemployed pool) instead of pointing at the
    # dead startup.
    config = replace(QUIET_CONFIG, n_startups=2, n_workers=1)
    model = TechnologyParkModel(config=config)
    failing, _surviving = model.startups
    worker = model.workers[0]
    worker.employed_by = failing.startup_id  # simulate prior employment
    failing.capital = 1.0  # burn (1.0) drives it to failure this period
    record = model.advance()
    assert record["exit_count_by_type"]["failure"] == 1
    assert worker.employed_by is None


def test_no_worker_is_employed_by_a_dead_startup() -> None:
    # Invariant behind the layoff fix: after any period, every worker's
    # employed_by is either None (unemployed) or a currently active startup.
    model = TechnologyParkModel(config=ModelConfig(seed=4, n_workers=8))
    total_exits = 0
    for _ in range(60):
        record = model.advance()
        total_exits += sum(record["exit_count_by_type"].values())
        active_ids = {startup.startup_id for startup in model.active_startups}
        for worker in model.workers:
            assert worker.employed_by is None or worker.employed_by in active_ids
    assert total_exits > 0  # the run actually exercised exits


def test_reputation_rises_with_survival() -> None:
    model = TechnologyParkModel(config=replace(QUIET_CONFIG, n_startups=2))
    for _ in range(5):
        model.advance()
    assert model.authority.reputation > 0.0


def test_reputation_falls_with_failure() -> None:
    config = replace(
        QUIET_CONFIG,
        n_startups=2,
        initial_capital=1.0,
        burn_rate=10.0,
    )
    model = TechnologyParkModel(config=config)
    model.authority.reputation = 0.5
    model.advance()
    assert model.authority.reputation < 0.5


def test_reputation_tracks_technology_quality() -> None:
    config = replace(
        QUIET_CONFIG,
        n_startups=1,
        rnd_share=1.0,
        knowledge_rnd_gain=1.0,
    )
    model = TechnologyParkModel(config=config)
    model.advance()
    startup = model.startups[0]
    assert startup.reputation == startup.technology_quality
    assert startup.reputation > 0.0


def test_partnership_reputation_weight_increases_ties() -> None:
    base = replace(
        QUIET_CONFIG,
        n_startups=2,
        partnership_attempts_per_startup=1,
        partnership_base_probability=0.0,
        partnership_compatibility_weight=0.0,
        partnership_complementarity_weight=0.0,
        partnership_cost_weight=0.0,
        rnd_share=1.0,
        knowledge_rnd_gain=0.5,
    )
    high = TechnologyParkModel(config=replace(base, partnership_reputation_weight=1.0))
    low = TechnologyParkModel(config=replace(base, partnership_reputation_weight=0.0))
    high_ties = 0
    low_ties = 0
    for _ in range(10):
        high_ties = high.advance()["partnership_tie_count"]
        low_ties = low.advance()["partnership_tie_count"]
    assert high_ties >= low_ties
    assert high_ties > 0


def test_ties_formed_counts_match_final_network_size() -> None:
    config = replace(
        QUIET_CONFIG,
        n_startups=4,
        partnership_attempts_per_startup=3,
        partnership_base_probability=1.0,
        partnership_dissolution_probability=0.0,
    )
    model = TechnologyParkModel(config=config)
    formed = 0
    record = model.metrics()
    for _ in range(5):
        record = model.advance()
        formed += record["ties_formed_by_type"]["partnership"]
    assert formed == 6
    assert record["partnership_tie_count"] == 6


def test_baseline_skeleton_is_preserved() -> None:
    record = TechnologyParkModel(config=replace(QUIET_CONFIG, n_startups=4)).advance()
    assert record["capital_total"] == 396.0
    assert record["knowledge_total"] == 0.0


def test_investor_access_reduces_burn() -> None:
    config = replace(
        QUIET_CONFIG,
        n_startups=2,
        burn_rate=2.0,
        investor_burn_relief=0.5,
    )
    model = TechnologyParkModel(config=config)
    model.startups[0].access_to_investors = 1.0
    model.advance()
    first, second = (startup.capital for startup in model.startups)
    assert first - second == 1.0


def test_relief_zero_disables_burn_effect() -> None:
    config = replace(
        QUIET_CONFIG,
        n_startups=2,
        burn_rate=2.0,
        investor_burn_relief=0.0,
    )
    model = TechnologyParkModel(config=config)
    model.startups[0].access_to_investors = 1.0
    model.advance()
    first, second = (startup.capital for startup in model.startups)
    assert first == second


def test_shock_collapses_configured_node_count() -> None:
    for nodes, expected in ((1, 1), (3, 3)):
        config = replace(
            QUIET_CONFIG,
            n_startups=3,
            shock_period=1,
            shock_type="central_firm",
            shock_nodes=nodes,
        )
        record = TechnologyParkModel(config=config).advance()
        assert record["exit_count_by_type"]["failure"] == expected


def test_quality_mean_and_cumulative_innovation_metrics() -> None:
    config = replace(
        QUIET_CONFIG,
        n_startups=3,
        rnd_share=1.0,
        knowledge_rnd_gain=0.5,
        innovation_event_threshold=0.1,
    )
    model = TechnologyParkModel(config=config)
    totals = []
    for _ in range(3):
        record = model.advance()
        totals.append(record["innovation_cumulative"])
        assert 0.0 < record["quality_mean"] <= 1.0
    assert totals == [3, 6, 9]
