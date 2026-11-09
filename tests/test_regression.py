import pytest

from technology_park_abm import ModelConfig, Policy, TechnologyParkModel

pytestmark = pytest.mark.regression

# V2-4 deliberate update: existing keys are byte-identical to v1.5.1 (no
# investors in these configs, so the burn relief never triggers); only the
# two additive V2-4 metrics were appended. Reason recorded here and in
# docs/final-report.md (v2.0.0 addendum).

GOLDEN_DEFAULT_SEED_7_PERIOD_10 = {
    "period": 10,
    "startup_count": 18,
    "active_startup_count": 18,
    "capital_total": 1981.3209438466336,
    "knowledge_total": 17.440303149896106,
    "entry_count": 1,
    "exit_count_by_type": {
        "failure": 0,
        "acquisition": 0,
        "voluntary": 0,
        "migration": 0,
    },
    "ties_formed_by_type": {
        "partnership": 4,
        "investment": 0,
        "hiring": 0,
    },
    "active_tie_count": 29,
    "partnership_tie_count": 29,
    "productive_tie_count": 15,
    "network_density": 0.1895424836601307,
    "degree_centralization": 0.18382352941176472,
    "knowledge_mean": 0.9689057305497837,
    "innovation_count": 3,
    "innovation_cumulative": 6,
    "quality_mean": 0.4745725402617052,
    "employment_total": 18,
    "reputation": 0.6513215599000001,
    "congestion": 1.8,
}

GOLDEN_POLICY_ANCHOR_SEED_3_PERIOD_10 = {
    "period": 10,
    "startup_count": 4,
    "active_startup_count": 4,
    "capital_total": 567.383219812142,
    "knowledge_total": 10.520474730762261,
    "entry_count": 0,
    "exit_count_by_type": {
        "failure": 0,
        "acquisition": 0,
        "voluntary": 0,
        "migration": 0,
    },
    "ties_formed_by_type": {
        "partnership": 0,
        "investment": 0,
        "hiring": 0,
    },
    "active_tie_count": 10,
    "partnership_tie_count": 10,
    "productive_tie_count": 1,
    "network_density": 1.0,
    "degree_centralization": 0.0,
    "knowledge_mean": 2.6301186826905654,
    "innovation_count": 0,
    "innovation_cumulative": 29,
    "quality_mean": 0.7241639242226537,
    "employment_total": 4,
    "reputation": 0.6513215599000001,
    "congestion": 0.5,
}


def test_deterministic_trajectory_matches_golden_record() -> None:
    model = TechnologyParkModel(seed=7)
    record = model.metrics()
    for _ in range(10):
        record = model.advance()
    assert record == GOLDEN_DEFAULT_SEED_7_PERIOD_10


def test_policy_anchor_trajectory_matches_golden_record() -> None:
    config = ModelConfig(
        seed=3,
        n_startups=4,
        n_anchor_firms=1,
        anchor_participation="active",
        entry_potential_per_period=0,
        policy=Policy(matchmaking=0.5),
    )
    model = TechnologyParkModel(config=config)
    record = model.metrics()
    for _ in range(10):
        record = model.advance()
    assert record == GOLDEN_POLICY_ANCHOR_SEED_3_PERIOD_10
