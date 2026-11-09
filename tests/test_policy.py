from dataclasses import replace

from technology_park_abm import ModelConfig, Policy, TechnologyParkModel

QUIET = ModelConfig(
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


def test_entry_subsidy_increases_entry() -> None:
    config = replace(
        QUIET,
        entry_potential_per_period=10,
        entry_base_probability=0.0,
        entry_reputation_weight=0.0,
        entry_funding_weight=0.0,
        entry_infrastructure_weight=0.0,
        entry_opportunity_weight=0.0,
        entry_cost_weight=0.0,
        policy=Policy(entry_subsidy=1.0),
    )
    record = TechnologyParkModel(config=config).advance()
    assert record["entry_count"] == 10


def test_matchmaking_increases_partnership_formation() -> None:
    config = replace(
        QUIET,
        n_startups=2,
        partnership_attempts_per_startup=1,
        partnership_base_probability=0.0,
        partnership_compatibility_weight=0.0,
        partnership_complementarity_weight=0.0,
        partnership_reputation_weight=0.0,
        partnership_cost_weight=0.0,
        policy=Policy(matchmaking=1.0),
    )
    record = TechnologyParkModel(config=config).advance()
    assert record["partnership_tie_count"] == 1


def test_shared_infrastructure_reduces_congestion_cost() -> None:
    config = replace(
        QUIET,
        n_startups=5,
        infrastructure_capacity=1.0,
        congestion_cost_per_org=2.0,
        policy=Policy(shared_infrastructure=1.0),
    )
    record = TechnologyParkModel(config=config).advance()
    assert record["congestion"] == 2.5
    assert record["capital_total"] == 465.0


def test_rnd_subsidy_increases_knowledge_gain() -> None:
    config = replace(
        QUIET,
        n_startups=1,
        rnd_share=1.0,
        knowledge_rnd_gain=1.0,
        policy=Policy(rnd_subsidy=1.0),
    )
    model = TechnologyParkModel(config=config)
    model.advance()
    assert model.startups[0].knowledge == 2.0


def test_talent_program_increases_hiring_knowledge() -> None:
    config = replace(
        QUIET,
        n_startups=1,
        n_workers=1,
        hiring_probability=1.0,
        policy=Policy(talent_program=1.0),
    )
    model = TechnologyParkModel(config=config)
    model.advance()
    assert model.startups[0].knowledge == 0.3


def test_investment_fund_increases_investor_capital() -> None:
    config = replace(
        QUIET,
        n_startups=1,
        n_investors=1,
        investment_probability=1.0,
        investment_min_quality=0.0,
        policy=Policy(investment_fund=100.0),
    )
    model = TechnologyParkModel(config=config)
    model.advance()
    assert model.investors[0].capital_available == 150.0


def test_central_firm_collapse_shock_causes_failure() -> None:
    config = replace(
        QUIET,
        n_startups=2,
        shock_period=1,
        shock_type="central_firm",
    )
    model = TechnologyParkModel(config=config)
    first, second = model.startups
    model.network.add_tie(first.startup_id, second.startup_id, "partnership", 1.0)
    record = model.advance()
    assert record["exit_count_by_type"]["failure"] == 1
    assert not first.alive


def test_funding_collapse_shock_deactivates_investors() -> None:
    config = replace(
        QUIET,
        n_startups=1,
        n_investors=1,
        shock_period=1,
        shock_type="funding",
    )
    model = TechnologyParkModel(config=config)
    model.advance()
    assert not model.investors[0].active
    assert model.investors[0].capital_available == 0.0
    assert model.startups[0].access_to_investors == 0.0


def test_invalid_shock_type_is_rejected() -> None:
    try:
        TechnologyParkModel(config=replace(QUIET, shock_period=1, shock_type="meteor"))
    except ValueError:
        pass
    else:
        raise AssertionError("invalid shock type should fail")


def test_invalid_shock_period_is_rejected() -> None:
    try:
        TechnologyParkModel(
            config=replace(QUIET, shock_period=0, shock_type="central_firm")
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid shock period should fail")
