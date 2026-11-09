from technology_park_abm import TechnologyParkModel, derive_stream_seed


def test_derive_stream_seed_is_deterministic_and_distinct() -> None:
    assert derive_stream_seed(7, "entry") == derive_stream_seed(7, "entry")
    assert derive_stream_seed(7, "entry") != derive_stream_seed(7, "exit")
    assert derive_stream_seed(7, "entry") != derive_stream_seed(8, "entry")


def test_streams_are_reproducible_for_same_seed() -> None:
    first = TechnologyParkModel(n_startups=0, seed=11)
    second = TechnologyParkModel(n_startups=0, seed=11)
    assert first.stream("entry").random() == second.stream("entry").random()


def test_streams_are_independent_across_names() -> None:
    first = TechnologyParkModel(n_startups=0, seed=11)
    second = TechnologyParkModel(n_startups=0, seed=11)
    assert first.stream("entry").random() != second.stream("exit").random()


def test_unknown_stream_is_rejected() -> None:
    model = TechnologyParkModel(n_startups=0, seed=0)
    try:
        model.stream("unknown")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown stream should fail")
