"""Experiment runners E1-E7 (docs/experiments.md, phase F4).

Every run persists a manifest (ADR 0003), one metrics row per scenario, seed,
and period, and final-period distributions per scenario. Scenarios with a
shock additionally carry recovery ratios (final vs. last pre-shock period)
and the share of seeds recovering at least 90% of pre-shock active startups
(E6, E7). Outputs are always labeled as simulation results, never as
empirical evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import ModelConfig, Policy
from .manifest import git_commit, git_dirty, mesa_version, package_version
from .metrics import METRIC_SCHEMA_VERSION
from .model import TechnologyParkModel

DEFAULT_PERIODS = 60
DEFAULT_SEEDS: tuple[int, ...] = (1, 2, 3)
EXPERIMENT_IDS: tuple[str, ...] = ("E1", "E2", "E3", "E4", "E5", "E6", "E7")
SUMMARY_METRICS: tuple[str, ...] = (
    "active_startup_count",
    "capital_total",
    "knowledge_total",
    "knowledge_mean",
    "innovation_count",
    "innovation_cumulative",
    "quality_mean",
    "partnership_tie_count",
    "degree_centralization",
    "entry_count",
    "exit_count_by_type_failure",
)
RECOVERY_METRICS: tuple[str, ...] = (
    "active_startup_count",
    "partnership_tie_count",
    "knowledge_total",
)
RECOVERY_THRESHOLD = 0.9


@dataclass(frozen=True)
class Scenario:
    """A named configuration within an experiment."""

    name: str
    config: ModelConfig
    playbook: str | None = None


@dataclass(frozen=True)
class ExperimentSpec:
    """An experiment made of baseline and counterfactual scenarios."""

    experiment_id: str
    description: str
    scenarios: tuple[Scenario, ...]


@dataclass(frozen=True)
class RunResult:
    """Outcome of an experiment suite run."""

    run_id: str
    rows: list[dict[str, Any]]
    summary: dict[str, dict[str, dict[str, float]]]
    manifest: dict[str, Any]


def build_experiments(periods: int) -> dict[str, ExperimentSpec]:
    """Build the E1-E6 scenario sets for a given horizon."""
    base = ModelConfig(
        n_startups=8,
        n_anchor_firms=0,
        n_universities=1,
        n_investors=2,
        n_workers=6,
        infrastructure_capacity=8.0,
        seed=0,
    )
    isolated = replace(base, entry_potential_per_period=0)
    policy_base = replace(base, investor_capital=10.0)
    # V2-4: must cover investment_amount (50) so the baseline actually
    # invests; otherwise the funding collapse cannot propagate (H6 retest).
    resilience_base = replace(base, investor_capital=100.0)
    shock_period = max(1, periods // 2)
    return {
        "E1": ExperimentSpec(
            "E1",
            "Critical mass: vary initial population",
            tuple(
                Scenario(f"startups_{count}", replace(isolated, n_startups=count))
                for count in (2, 8, 16)
            ),
        ),
        "E2": ExperimentSpec(
            "E2",
            "Diversity and specialization",
            (
                Scenario("concentrated", replace(isolated, sectors=("software",))),
                Scenario(
                    "complementary",
                    replace(
                        isolated,
                        sectors=("biotech", "energy", "hardware", "software"),
                        cross_sector_compatibility=0.25,
                        cross_sector_complementarity=0.5,
                    ),
                ),
                Scenario(
                    "unrelated",
                    replace(
                        isolated,
                        sectors=("biotech", "energy", "hardware", "software"),
                        cross_sector_compatibility=0.0,
                        cross_sector_complementarity=0.0,
                    ),
                ),
            ),
        ),
        "E3": ExperimentSpec(
            "E3",
            "Anchor participation",
            (
                Scenario("absent", isolated, playbook="fragmented"),
                Scenario(
                    "passive",
                    replace(
                        isolated,
                        n_anchor_firms=1,
                        anchor_participation="passive",
                    ),
                    playbook="passive-anchor",
                ),
                Scenario(
                    "active",
                    replace(
                        isolated,
                        n_anchor_firms=1,
                        anchor_participation="active",
                    ),
                    playbook="anchor-led",
                ),
                Scenario(
                    "multiple_active",
                    replace(
                        isolated,
                        n_anchor_firms=3,
                        anchor_participation="active",
                    ),
                    playbook="anchor-led-multi",
                ),
            ),
        ),
        "E4": ExperimentSpec(
            "E4",
            "Policy instruments",
            (
                Scenario("baseline", policy_base, playbook="baseline"),
                Scenario(
                    "entry_subsidy",
                    replace(policy_base, policy=Policy(entry_subsidy=0.5)),
                    playbook="entry-subsidy",
                ),
                Scenario(
                    "rnd_subsidy",
                    replace(policy_base, policy=Policy(rnd_subsidy=0.5)),
                    playbook="rnd-led",
                ),
                Scenario(
                    "shared_infrastructure",
                    replace(policy_base, policy=Policy(shared_infrastructure=0.5)),
                    playbook="infrastructure-intensive",
                ),
                Scenario(
                    "matchmaking",
                    replace(policy_base, policy=Policy(matchmaking=0.5)),
                    playbook="science-driven",
                ),
                Scenario(
                    "talent_program",
                    replace(policy_base, policy=Policy(talent_program=0.5)),
                    playbook="talent-led",
                ),
                Scenario(
                    "investment_fund",
                    replace(policy_base, policy=Policy(investment_fund=90.0)),
                    playbook="vc-backed",
                ),
            ),
        ),
        "E5": ExperimentSpec(
            "E5",
            "Congestion: population with fixed infrastructure",
            tuple(
                Scenario(
                    f"population_{count}",
                    replace(
                        isolated,
                        n_startups=count,
                        infrastructure_capacity=8.0,
                    ),
                )
                for count in (4, 8, 16)
            ),
        ),
        "E6": ExperimentSpec(
            "E6",
            "Resilience: central firm or funding collapse",
            (
                Scenario("baseline", resilience_base, playbook="baseline"),
                Scenario(
                    "central_firm_collapse",
                    replace(
                        resilience_base,
                        shock_period=shock_period,
                        shock_type="central_firm",
                        shock_nodes=3,
                    ),
                    playbook="shock-central",
                ),
                Scenario(
                    "funding_collapse",
                    replace(
                        resilience_base,
                        shock_period=shock_period,
                        shock_type="funding",
                    ),
                    playbook="shock-funding",
                ),
            ),
        ),
        "E7": ExperimentSpec(
            "E7",
            "Distributedness and resilience: network structure mediates "
            "recovery from a central-agent departure (H6)",
            (
                Scenario(
                    "hub",
                    replace(
                        resilience_base,
                        partnership_reputation_weight=0.6,
                        shock_period=shock_period,
                        shock_type="central_firm",
                        shock_nodes=3,
                    ),
                    playbook="shock-central",
                ),
                Scenario(
                    "distributed",
                    replace(
                        resilience_base,
                        sectors=("biotech", "energy", "hardware", "software"),
                        cross_sector_compatibility=0.5,
                        cross_sector_complementarity=0.5,
                        partnership_reputation_weight=0.0,
                        shock_period=shock_period,
                        shock_type="central_firm",
                        shock_nodes=3,
                    ),
                    playbook="shock-central",
                ),
            ),
        ),
    }


@dataclass(frozen=True)
class _RunTask:
    """One independent (scenario, seed) run; picklable for process pools."""

    experiment_id: str
    scenario: Scenario
    seed: int
    periods: int


def _run_task(task: _RunTask) -> list[dict[str, Any]]:
    config = replace(task.scenario.config, seed=task.seed)
    model = TechnologyParkModel(config=config)
    return [
        _flatten_record(
            task.experiment_id, task.scenario.name, task.seed, model.advance()
        )
        for _ in range(task.periods)
    ]


def run_experiment_suite(
    experiment_id: str,
    seeds: Sequence[int],
    periods: int,
    run_id: str | None = None,
    jobs: int = 1,
) -> RunResult:
    """Run every scenario of an experiment across seeds and periods.

    ``jobs`` parallelizes the independent (scenario, seed) runs across worker
    processes. Rows are assembled in deterministic scenario/seed/period order,
    so the result is identical for any ``jobs`` value.
    """
    if not seeds:
        raise ValueError("seeds must not be empty")
    if periods < 1:
        raise ValueError("periods must be at least 1")
    if jobs < 1:
        raise ValueError("jobs must be at least 1")
    specs = build_experiments(periods)
    if experiment_id not in specs:
        raise ValueError(f"unknown experiment: {experiment_id}")
    spec = specs[experiment_id]
    tasks = [
        _RunTask(spec.experiment_id, scenario, seed, periods)
        for scenario in spec.scenarios
        for seed in seeds
    ]
    if jobs > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=min(jobs, len(tasks))) as pool:
            chunks = list(pool.map(_run_task, tasks))
    else:
        chunks = [_run_task(task) for task in tasks]
    rows: list[dict[str, Any]] = []
    for chunk in chunks:
        rows.extend(chunk)
    resolved_run_id = run_id or _default_run_id(spec.experiment_id)
    manifest = _build_run_manifest(spec, seeds, periods)
    manifest["run_id"] = resolved_run_id
    summary = _summarize(rows, spec)
    return RunResult(
        run_id=resolved_run_id,
        rows=rows,
        summary=summary,
        manifest=manifest,
    )


def _flatten_record(
    experiment_id: str,
    scenario: str,
    seed: int,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "experiment": experiment_id,
        "scenario": scenario,
        "seed": seed,
    }
    for key, value in record.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                row[f"{key}_{sub_key}"] = sub_value
        else:
            row[key] = value
    return row


def _summarize(
    rows: Sequence[Mapping[str, Any]],
    spec: ExperimentSpec,
) -> dict[str, dict[str, dict[str, float]]]:
    by_seed: dict[tuple[str, int], dict[int, Mapping[str, Any]]] = {}
    for row in rows:
        key = (str(row["scenario"]), int(row["seed"]))
        by_seed.setdefault(key, {})[int(row["period"])] = row
    samples: dict[str, dict[str, list[float]]] = {}
    for (scenario, _seed), periods_map in by_seed.items():
        final_row = periods_map[max(periods_map)]
        for metric in SUMMARY_METRICS:
            samples.setdefault(scenario, {}).setdefault(metric, []).append(
                float(final_row[metric])
            )
    summary = {
        scenario: {metric: _distribution(values) for metric, values in metrics.items()}
        for scenario, metrics in samples.items()
    }
    _add_recovery_metrics(summary, by_seed, spec)
    return summary


def _add_recovery_metrics(
    summary: dict[str, dict[str, dict[str, float]]],
    by_seed: Mapping[tuple[str, int], Mapping[int, Mapping[str, Any]]],
    spec: ExperimentSpec,
) -> None:
    """Add post-shock recovery ratios for scenarios with a shock configured.

    The shock fires during the step that ends at ``shock_period``, so the last
    pre-shock record is period ``shock_period - 1``. Recovery is the final
    value divided by that baseline, per seed; ``recovery_90pct`` is the
    0/1 indicator of recovering at least 90% of pre-shock active startups
    (its mean is the share of seeds that recover). ``baseline_degree_centralization``
    carries the pre-shock network structure, the distributedness marker for
    H6 (E7). Scenarios with ``shock_period < 2`` have no pre-shock record and
    are skipped.
    """
    shock_periods = {
        scenario.name: scenario.config.shock_period for scenario in spec.scenarios
    }
    for scenario_name, shock_period in shock_periods.items():
        if shock_period is None or shock_period < 2:
            continue
        baseline_period = shock_period - 1
        ratios: dict[str, list[float]] = {metric: [] for metric in RECOVERY_METRICS}
        recovered: list[float] = []
        baseline_centralization: list[float] = []
        for (scenario, _seed), periods_map in by_seed.items():
            if scenario != scenario_name:
                continue
            baseline = periods_map.get(baseline_period)
            final_row = periods_map[max(periods_map)]
            if baseline is None:
                continue
            for metric in RECOVERY_METRICS:
                base_value = float(baseline[metric])
                if base_value > 0.0:
                    ratios[metric].append(float(final_row[metric]) / base_value)
            base_active = float(baseline["active_startup_count"])
            if base_active > 0.0:
                ratio = float(final_row["active_startup_count"]) / base_active
                recovered.append(1.0 if ratio >= RECOVERY_THRESHOLD else 0.0)
            baseline_centralization.append(float(baseline["degree_centralization"]))
        if not ratios["active_startup_count"]:
            continue
        for metric, values in ratios.items():
            if values:
                summary[scenario_name][f"recovery_{metric}"] = _distribution(values)
        if recovered:
            summary[scenario_name]["recovery_90pct"] = _distribution(recovered)
        if baseline_centralization:
            summary[scenario_name]["baseline_degree_centralization"] = _distribution(
                baseline_centralization
            )


def _distribution(values: list[float]) -> dict[str, float]:
    """Summary statistics of a sample across seeds.

    Quantiles use the inclusive method (linear interpolation, matching
    ``numpy.percentile`` defaults), so p10/p90 always stay within
    [min, max] even for small seed counts.
    """
    ordered = sorted(values)
    stats = {
        "count": float(len(ordered)),
        "mean": statistics.fmean(ordered),
        "min": ordered[0],
        "max": ordered[-1],
        "median": statistics.median(ordered),
    }
    if len(ordered) >= 2:
        quantiles = statistics.quantiles(ordered, n=4, method="inclusive")
        stats["q1"] = quantiles[0]
        stats["q3"] = quantiles[2]
        deciles = statistics.quantiles(ordered, n=10, method="inclusive")
        stats["p10"] = deciles[0]
        stats["p90"] = deciles[8]
    return stats


def _build_run_manifest(
    spec: ExperimentSpec,
    seeds: Sequence[int],
    periods: int,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "created_utc": datetime.now(UTC).isoformat(),
        "notice": "Simulation output; not empirical evidence.",
        "experiment": {
            "id": spec.experiment_id,
            "description": spec.description,
            "periods": periods,
            "seeds": list(seeds),
            "scenarios": {
                scenario.name: asdict(scenario.config) for scenario in spec.scenarios
            },
            "playbooks": {
                scenario.name: scenario.playbook for scenario in spec.scenarios
            },
        },
        "model": {
            "package_version": package_version(),
            "metric_schema_version": METRIC_SCHEMA_VERSION,
            "git_commit": git_commit(),
            "git_dirty": git_dirty(),
        },
        "environment": {
            "python": platform.python_version(),
            "mesa": mesa_version(),
            "platform": platform.platform(),
        },
        "outputs": {"metrics": "metrics.csv", "summary": "summary.json"},
    }


def _default_run_id(experiment_id: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    short_hash = (git_commit() or "nogit")[:7]
    return f"{experiment_id}-{stamp}-{short_hash}"


def persist_run(result: RunResult, output_root: Path = Path("results")) -> Path:
    """Write manifest, metrics, and summary files for a run."""
    run_dir = output_root / result.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(result.manifest, indent=2), encoding="utf-8"
    )
    fieldnames = list(result.rows[0].keys())
    with (run_dir / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result.rows)
    (run_dir / "summary.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return run_dir


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E1-E7 experiment suites.")
    parser.add_argument("experiment", choices=[*EXPERIMENT_IDS, "all"])
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    parser.add_argument("--periods", type=int, default=DEFAULT_PERIODS)
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Worker processes for the independent (scenario, seed) runs.",
    )
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args(argv)
    if args.periods < 1:
        parser.error("--periods must be at least 1")
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    names = list(EXPERIMENT_IDS) if args.experiment == "all" else [args.experiment]
    for name in names:
        result = run_experiment_suite(
            name, tuple(args.seeds), args.periods, jobs=args.jobs
        )
        run_dir = persist_run(result, args.output)
        print(f"{name}: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
