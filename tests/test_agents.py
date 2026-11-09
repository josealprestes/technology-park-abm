from technology_park_abm import (
    AnchorFirm,
    Investor,
    Startup,
    TechnologyParkModel,
    University,
    Worker,
)


def _model() -> TechnologyParkModel:
    return TechnologyParkModel(n_startups=0, seed=0)


def test_startup_initial_state() -> None:
    startup = Startup(_model(), sector="software", initial_capital=50.0)
    assert startup.sector == "software"
    assert startup.capital == 50.0
    assert startup.technology_quality == 0.0
    assert startup.knowledge == 0.0
    assert startup.reputation == 0.0
    assert startup.team_size == 1
    assert startup.age == 0
    assert startup.access_to_clients == 0.0
    assert startup.access_to_investors == 0.0
    assert startup.alive
    assert startup.can_act
    assert isinstance(startup.startup_id, int)


def test_startup_exits_at_exactly_zero_capital() -> None:
    startup = Startup(_model(), sector="software", initial_capital=1.0)
    startup.step(burn_rate=1.0)
    assert startup.capital == 0.0
    assert not startup.alive
    assert startup.exit_type == "failure"


def test_startup_exit_records_type() -> None:
    startup = Startup(_model(), sector="software")
    startup.exit("acquisition")
    assert not startup.alive
    assert startup.exit_type == "acquisition"
    assert not startup.can_act


def test_invalid_exit_type_is_rejected() -> None:
    startup = Startup(_model(), sector="software")
    try:
        startup.exit("bankruptcy")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid exit type should fail")


def test_dead_startup_is_inert() -> None:
    startup = Startup(_model(), sector="software", initial_capital=1.0)
    startup.step(burn_rate=1.0)
    assert not startup.can_act
    age_after_exit = startup.age
    startup.step(burn_rate=1.0)
    assert startup.age == age_after_exit
    assert startup.capital == 0.0
    assert not startup.alive


def test_negative_initial_capital_is_rejected() -> None:
    try:
        Startup(_model(), sector="software", initial_capital=-1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("negative initial capital should fail")


def test_invalid_anchor_participation_is_rejected() -> None:
    try:
        AnchorFirm(_model(), sector="software", participation="dormant")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid participation should fail")


def test_anchor_keeps_configured_state() -> None:
    anchor = AnchorFirm(_model(), sector="software", participation="active")
    assert anchor.sector == "software"
    assert anchor.capital == 1000.0
    assert anchor.participation == "active"
    assert anchor.can_act


def test_anchor_knowledge_sets_quality() -> None:
    anchor = AnchorFirm(_model(), sector="software", knowledge=5.0)
    assert anchor.knowledge == 5.0
    assert anchor.technology_quality == 5.0 / 6.0


def test_negative_anchor_capital_is_rejected() -> None:
    try:
        AnchorFirm(_model(), sector="software", capital=-1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("negative anchor capital should fail")


def test_university_defaults() -> None:
    university = University(_model())
    assert university.research_quality == 0.5
    assert university.knowledge_stock == 0.0
    assert university.technology_transfer_activity == 0.0


def test_investor_defaults_and_validation() -> None:
    investor = Investor(_model())
    assert investor.capital_available == 100.0
    assert investor.risk_appetite == 0.5
    assert investor.active
    try:
        Investor(_model(), capital_available=-1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("negative available capital should fail")


def test_invalid_university_values_are_rejected() -> None:
    try:
        University(_model(), research_quality=1.5)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid research quality should fail")
    try:
        University(_model(), knowledge_stock=-1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("negative knowledge stock should fail")


def test_invalid_investor_risk_appetite_is_rejected() -> None:
    try:
        Investor(_model(), risk_appetite=-0.1)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid risk appetite should fail")


def test_invalid_worker_skill_is_rejected() -> None:
    try:
        Worker(_model(), skill=1.5)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid skill should fail")


def test_invalid_worker_education_is_rejected() -> None:
    try:
        Worker(_model(), education="doutorado")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid education should fail")


def test_worker_defaults() -> None:
    worker = Worker(_model(), sector="biotech", skill=0.8)
    assert worker.sector == "biotech"
    assert worker.skill == 0.8
    assert worker.employed_by is None
