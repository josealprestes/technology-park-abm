from technology_park_abm import Environment, ModelConfig, Policy, SectorSpace


def test_sector_space_defaults_and_symmetry() -> None:
    space = SectorSpace(sectors=("biotech", "software"))
    assert space.compatibility("biotech", "biotech") == 1.0
    assert space.compatibility("biotech", "software") == 0.25
    assert space.compatibility("software", "biotech") == space.compatibility(
        "biotech", "software"
    )
    assert space.complementarity("biotech", "biotech") == 0.5
    assert space.complementarity("biotech", "software") == 0.5
    assert space.complementarity("software", "biotech") == space.complementarity(
        "biotech", "software"
    )


def test_unknown_sector_is_rejected() -> None:
    space = SectorSpace(sectors=("biotech",))
    try:
        space.compatibility("biotech", "mining")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown sector should fail")


def test_empty_sector_space_is_rejected() -> None:
    try:
        SectorSpace(sectors=())
    except ValueError:
        pass
    else:
        raise AssertionError("empty sector space should fail")


def test_sector_values_must_be_in_unit_interval() -> None:
    try:
        SectorSpace(sectors=("a",), cross_sector_compatibility=2.0)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range compatibility should fail")


def test_environment_from_config() -> None:
    config = ModelConfig(
        infrastructure_capacity=2.0,
        funding_conditions=0.5,
        labor_market_slack=3.0,
    )
    environment = Environment.from_config(config)
    assert environment.infrastructure_capacity == 2.0
    assert environment.infrastructure_load == 0.0
    assert environment.funding_conditions == 0.5
    assert environment.labor_market_slack == 3.0
    assert environment.policy == Policy()
    assert environment.sector_space.sectors == config.sectors


def test_negative_environment_values_are_rejected() -> None:
    space = SectorSpace(sectors=("a",))
    try:
        Environment(sector_space=space, infrastructure_load=-1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("negative infrastructure load should fail")
