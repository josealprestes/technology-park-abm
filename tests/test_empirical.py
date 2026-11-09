"""Empirical attribute distributions, microdata loading, and initialization."""

from __future__ import annotations

import random
from pathlib import Path

from technology_park_abm import ModelConfig, TechnologyParkModel
from technology_park_abm.empirical import (
    AGGREGATE_SOURCES,
    ANCHOR_SAMPLE,
    EDUCATION_LEVELS,
    load_microdata,
    sample_anchor_capital,
    sample_research_quality,
    sample_worker,
    sector_proximity,
)


def test_worker_marginals_match_published_shares() -> None:
    rng = random.Random(7)
    samples = [sample_worker(rng) for _ in range(2000)]
    superior_share = sum(
        1 for sample in samples if sample["education"] == "superior"
    ) / len(samples)
    assert 0.25 < superior_share < 0.35
    means = {
        education: sum(
            sample["wage"] for sample in samples if sample["education"] == education
        )
        / max(1, sum(1 for sample in samples if sample["education"] == education))
        for education in EDUCATION_LEVELS
    }
    assert means["superior"] > means["medio"] > means["fundamental"]


def test_aggregates_match_rais_education_shares() -> None:
    rng = random.Random(21)
    samples = [sample_worker(rng) for _ in range(5000)]
    for education, expected in (
        ("fundamental", 0.138),
        ("medio", 0.550),
        ("superior", 0.312),
    ):
        count = sum(1 for sample in samples if sample["education"] == education)
        share = count / len(samples)
        assert abs(share - expected) < 0.02, (education, share)


def test_aggregates_match_rais_age_structure() -> None:
    rng = random.Random(22)
    samples = [sample_worker(rng) for _ in range(3000)]
    ages = [sample["age"] for sample in samples]
    assert 37.0 < sum(ages) / len(ages) < 40.0
    young = sum(1 for age in ages if 18 <= age <= 24) / len(ages)
    assert abs(young - 0.134) < 0.02


def test_education_wage_joint_pattern_matches_pnad() -> None:
    rng = random.Random(23)
    samples = [sample_worker(rng) for _ in range(3000)]
    means = {
        education: sum(
            sample["wage"] for sample in samples if sample["education"] == education
        )
        / max(1, sum(1 for sample in samples if sample["education"] == education))
        for education in EDUCATION_LEVELS
    }
    assert means["superior"] > means["medio"] > means["fundamental"]
    assert 1.8 < means["superior"] / means["medio"] < 3.2
    assert 1.0 < means["medio"] / means["fundamental"] < 1.5


def test_aggregate_sources_are_documented() -> None:
    for key in ("education", "age", "wage"):
        assert AGGREGATE_SOURCES[key]
    assert "RAIS" in AGGREGATE_SOURCES["education"]
    assert "PNAD" in AGGREGATE_SOURCES["wage"]


def test_worker_skill_is_bounded_and_ordered() -> None:
    rng = random.Random(3)
    samples = [sample_worker(rng) for _ in range(500)]
    assert all(0.0 < sample["skill"] <= 1.0 for sample in samples)
    skill_by_education = {
        education: sum(
            sample["skill"] for sample in samples if sample["education"] == education
        )
        / max(1, sum(1 for sample in samples if sample["education"] == education))
        for education in EDUCATION_LEVELS
    }
    assert skill_by_education["superior"] > skill_by_education["fundamental"]


def test_sampling_is_deterministic() -> None:
    first = [sample_worker(random.Random(11)) for _ in range(5)]
    second = [sample_worker(random.Random(11)) for _ in range(5)]
    assert first == second
    assert sample_research_quality(random.Random(3)) == sample_research_quality(
        random.Random(3)
    )


def test_microdata_loader_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "workers.csv"
    path.write_text(
        "education,age,wage,skill\nsuperior,40,6.5,0.9\nmedio,25,2.0,0.5\n",
        encoding="utf-8",
    )
    rows = load_microdata(path)
    assert len(rows) == 2
    worker = sample_worker(random.Random(1), rows)
    assert worker["education"] in {"superior", "medio"}
    assert worker["skill"] > 0.0


def test_microdata_missing_columns_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("education,age\nmedio,30\n", encoding="utf-8")
    try:
        load_microdata(path)
    except ValueError:
        pass
    else:
        raise AssertionError("missing columns should fail")


def test_microdata_contract_violations_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "invalid.csv"
    path.write_text(
        "education,age,wage,skill\nsuperior,40,6.5,0.9\nmedio,300,2.0,0.5\n",
        encoding="utf-8",
    )
    try:
        load_microdata(path)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range age should fail the data contract")


def test_microdata_empty_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("education,age,wage,skill\n", encoding="utf-8")
    try:
        load_microdata(path)
    except ValueError:
        pass
    else:
        raise AssertionError("empty microdata should fail")


def test_model_empirical_init_sets_heterogeneous_attributes() -> None:
    config = ModelConfig(
        seed=5,
        n_startups=4,
        n_workers=6,
        empirical_init="aggregates",
        entry_potential_per_period=0,
    )
    model = TechnologyParkModel(config=config)
    skills = {round(worker.skill, 4) for worker in model.workers}
    assert len(skills) > 1
    assert all(0.0 < skill <= 1.0 for skill in skills)
    assert all(worker.education in EDUCATION_LEVELS for worker in model.workers)


def test_model_empirical_init_is_deterministic() -> None:
    config = ModelConfig(
        seed=5,
        n_workers=4,
        empirical_init="aggregates",
        entry_potential_per_period=0,
    )
    first = TechnologyParkModel(config=config)
    second = TechnologyParkModel(config=config)
    assert [worker.skill for worker in first.workers] == [
        worker.skill for worker in second.workers
    ]
    assert [worker.education for worker in first.workers] == [
        worker.education for worker in second.workers
    ]


def test_anchor_capital_sample_uses_real_range() -> None:
    rng = random.Random(9)
    draws = [sample_anchor_capital(rng) for _ in range(200)]
    assert all(
        ANCHOR_SAMPLE["capital_min_brl_billions"] - 1e-9
        <= draw
        <= ANCHOR_SAMPLE["capital_max_brl_billions"] + 1e-9
        for draw in draws
    )
    repeated_rng = random.Random(9)
    repeated = [sample_anchor_capital(repeated_rng) for _ in range(200)]
    assert draws == repeated


def test_sector_proximity_is_symmetric_and_bounded() -> None:
    for first in ("software", "hardware", "energy", "biotech", "unknown"):
        for second in ("software", "hardware", "energy", "biotech", "unknown"):
            value = sector_proximity(first, second)
            assert 0.0 <= value <= 1.0
            assert value == sector_proximity(second, first)
    assert sector_proximity("software", "software") == 1.0
    assert sector_proximity("unknown", "software") == 0.0


def test_invalid_empirical_mode_is_rejected() -> None:
    try:
        TechnologyParkModel(config=ModelConfig(empirical_init="magic"))
    except ValueError:
        pass
    else:
        raise AssertionError("invalid empirical mode should fail")


def test_microdata_mode_requires_path() -> None:
    try:
        TechnologyParkModel(config=ModelConfig(empirical_init="microdata"))
    except ValueError:
        pass
    else:
        raise AssertionError("microdata mode without path should fail")
