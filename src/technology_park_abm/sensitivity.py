"""One-at-a-time sensitivity analysis and uncertainty reporting (phase F6)."""

from __future__ import annotations

import argparse
import json
import math
import platform
import random
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import asdict, replace
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any, cast

from .config import ModelConfig
from .manifest import git_commit, git_dirty, mesa_version, package_version
from .metrics import METRIC_SCHEMA_VERSION
from .model import TechnologyParkModel

DEFAULT_PARAMETERS: tuple[str, ...] = (
    "burn_rate",
    "entry_reputation_weight",
    "partnership_compatibility_weight",
    "knowledge_spillover_rate",
    "congestion_cost_per_org",
    "initial_capital",
)
DEFAULT_FACTORS: tuple[float, ...] = (0.5, 1.5)
DEFAULT_OUTPUT_KEYS: tuple[str, ...] = (
    "active_startup_count",
    "knowledge_total",
    "innovation_count",
    "capital_total",
)

GSA_PARAMETERS: tuple[str, ...] = (
    "burn_rate",
    "initial_capital",
    "entry_potential_per_period",
    "entry_base_probability",
    "entry_reputation_weight",
    "partnership_attempts_per_startup",
    "partnership_base_probability",
    "partnership_compatibility_weight",
    "knowledge_rnd_gain",
    "knowledge_spillover_rate",
    "congestion_cost_per_org",
    "voluntary_exit_probability",
)

GSA_DESIGN_SEED = 20261007

# History-matching pilot (V2-5): the two dominant parameters from the
# sensitivity report, ruled against wide stylized bands from the validation
# report (park alive, network alive, knowledge accumulates without exploding).
# Bands are deliberately wide: this pilot establishes the method
# (deterministic, budgeted, reported), not a calibration.
HM_PARAMETERS: tuple[str, ...] = ("congestion_cost_per_org", "initial_capital")
HM_TARGETS: tuple[tuple[str, float, float, float], ...] = (
    # (metric, band_low, band_high, floor_sd)
    ("active_startup_count", 3.0, 30.0, 1.0),
    ("partnership_tie_count", 5.0, 80.0, 2.0),
    ("knowledge_total", 5.0, 60.0, 2.0),
)
HM_LEVELS = 5
HM_CUTOFF = 3.0


def mean_outputs(
    config: ModelConfig,
    seeds: Sequence[int],
    periods: int,
    output_keys: Sequence[str],
) -> dict[str, float]:
    """Mean final-period outputs across seeds for one configuration."""
    if not seeds:
        raise ValueError("seeds must not be empty")
    totals = {key: 0.0 for key in output_keys}
    for seed in seeds:
        model = TechnologyParkModel(config=replace(config, seed=seed))
        record: Mapping[str, Any] = cast(Mapping[str, Any], model.metrics())
        for _ in range(periods):
            record = cast(Mapping[str, Any], model.advance())
        for key in output_keys:
            totals[key] += float(record[key])
    return {key: value / len(seeds) for key, value in totals.items()}


def _require_parameter(config: ModelConfig, name: str) -> None:
    if not hasattr(config, name):
        raise ValueError(f"unknown config parameter: {name}")


def one_at_a_time(
    parameters: Sequence[str],
    factors: Sequence[float],
    seeds: Sequence[int],
    periods: int,
    output_keys: Sequence[str],
    base_config: ModelConfig | None = None,
) -> dict[str, Any]:
    """Vary one parameter at a time and compare mean outputs to the baseline."""
    if periods < 1:
        raise ValueError("periods must be at least 1")
    base = base_config or ModelConfig()
    baseline = mean_outputs(base, seeds, periods, output_keys)
    variations: dict[str, Any] = {}
    for name in parameters:
        _require_parameter(base, name)
        base_value = getattr(base, name)
        for factor in factors:
            value = base_value * factor
            config = replace(base, **{name: value})
            variations[f"{name}={value:.6g}"] = {
                "parameter": name,
                "factor": factor,
                "value": value,
                "outputs": mean_outputs(config, seeds, periods, output_keys),
            }
    return {"baseline": baseline, "variations": variations}


def two_way_interaction(
    parameter_a: str,
    value_a: float,
    parameter_b: str,
    value_b: float,
    seeds: Sequence[int],
    periods: int,
    output_keys: Sequence[str],
    base_config: ModelConfig | None = None,
) -> dict[str, Any]:
    """Probe whether two parameters interact (joint effect vs sum of singles).

    OAT designs cannot detect interactions; this compares baseline, each
    parameter alone, and both together. A nonzero ``interaction`` entry is the
    classic sign that the two parameters act non-additively.
    """
    if periods < 1:
        raise ValueError("periods must be at least 1")
    base = base_config or ModelConfig()
    _require_parameter(base, parameter_a)
    _require_parameter(base, parameter_b)
    baseline = mean_outputs(base, seeds, periods, output_keys)
    overrides_a: dict[str, Any] = {parameter_a: value_a}
    overrides_b: dict[str, Any] = {parameter_b: value_b}
    overrides_both: dict[str, Any] = {
        parameter_a: value_a,
        parameter_b: value_b,
    }
    only_a = mean_outputs(replace(base, **overrides_a), seeds, periods, output_keys)
    only_b = mean_outputs(replace(base, **overrides_b), seeds, periods, output_keys)
    both = mean_outputs(replace(base, **overrides_both), seeds, periods, output_keys)
    interaction = {
        key: (both[key] - baseline[key])
        - ((only_a[key] - baseline[key]) + (only_b[key] - baseline[key]))
        for key in output_keys
    }
    return {
        "parameter_a": parameter_a,
        "value_a": value_a,
        "parameter_b": parameter_b,
        "value_b": value_b,
        "baseline": baseline,
        "only_a": only_a,
        "only_b": only_b,
        "both": both,
        "interaction": interaction,
    }


def _bounds_for(config: ModelConfig, name: str) -> tuple[float, float]:
    default = getattr(config, name)
    if isinstance(default, int):
        low_int = max(1, int(default) // 2)
        high_int = max(low_int + 1, int(default) * 2)
        return float(low_int), float(high_int)
    value = float(default)
    low = max(0.0, value * 0.5)
    high = value * 1.5 if value > 0.0 else 0.5
    if (
        name.endswith("_probability")
        or name.endswith("_rate")
        or name.endswith("_share")
    ):
        high = min(1.0, high)
    return low, high


def _coerce_value(config: ModelConfig, name: str, value: float) -> Any:
    default = getattr(config, name)
    if isinstance(default, int):
        return int(round(value))
    return float(value)


def _config_for_point(
    base: ModelConfig,
    names: Sequence[str],
    values: Mapping[str, float],
) -> ModelConfig:
    overrides: dict[str, Any] = {
        name: _coerce_value(base, name, values[name]) for name in names
    }
    return replace(base, **overrides)


def morris_effect_stats(
    parameters: Sequence[str],
    output_keys: Sequence[str],
    effects: Mapping[str, Mapping[str, Sequence[float]]],
    bounds: Mapping[str, tuple[float, float]],
) -> dict[str, Any]:
    """mu* and sigma per parameter/output from elementary-effect lists.

    ``mu_star`` is the mean absolute elementary effect (overall importance),
    ``sigma`` its sample standard deviation (ddof=1, non-linearity and
    interaction indicator, matching SALib and the Morris literature), and
    ``mu_star_range`` scales mu* back to output units over the parameter
    span. Extracted as a pure core so the estimators can be cross-validated
    against SALib (tests/test_gsa_crosscheck.py).
    """
    results: dict[str, Any] = {}
    for name in parameters:
        results[name] = {}
        span = bounds[name][1] - bounds[name][0]
        for key in output_keys:
            values = list(effects[name][key])
            mean_abs = statistics.fmean(abs(value) for value in values)
            results[name][key] = {
                "mu_star": mean_abs,
                "mu_star_range": mean_abs * span,
                "sigma": statistics.stdev(values) if len(values) > 1 else 0.0,
            }
    return results


def morris_screen(
    parameters: Sequence[str],
    seeds: Sequence[int],
    periods: int,
    output_keys: Sequence[str],
    base_config: ModelConfig | None = None,
    trajectories: int = 8,
    levels: int = 4,
    design_seed: int = GSA_DESIGN_SEED,
) -> dict[str, Any]:
    """Morris elementary-effects screening (mu* and sigma) for screening.

    Each trajectory moves one parameter at a time on a regular grid. A high
    sigma relative to mu* signals non-linearity or interaction, which OAT
    designs cannot see.
    """
    if periods < 1:
        raise ValueError("periods must be at least 1")
    if levels < 2:
        raise ValueError("levels must be at least 2")
    base = base_config or ModelConfig()
    bounds = {name: _bounds_for(base, name) for name in parameters}
    grid = {
        name: [low + k * (high - low) / (levels - 1) for k in range(levels)]
        for name, (low, high) in bounds.items()
    }
    rng = random.Random(design_seed)
    effects: dict[str, dict[str, list[float]]] = {
        name: {key: [] for key in output_keys} for name in parameters
    }
    for _ in range(trajectories):
        order = list(parameters)
        rng.shuffle(order)
        indices = {name: rng.randrange(levels - 1) for name in parameters}
        point = {name: grid[name][indices[name]] for name in parameters}
        previous = mean_outputs(
            _config_for_point(base, parameters, point),
            seeds,
            periods,
            output_keys,
        )
        for name in order:
            indices[name] += 1
            point = {key: grid[key][indices[key]] for key in parameters}
            outputs = mean_outputs(
                _config_for_point(base, parameters, point),
                seeds,
                periods,
                output_keys,
            )
            delta = grid[name][1] - grid[name][0]
            for key in output_keys:
                effects[name][key].append((outputs[key] - previous[key]) / delta)
            previous = outputs
    return {
        "parameters": list(parameters),
        "trajectories": trajectories,
        "levels": levels,
        "bounds": {name: list(bounds[name]) for name in parameters},
        "effects": morris_effect_stats(parameters, output_keys, effects, bounds),
    }


def sobol_indices_from_outputs(
    parameters: Sequence[str],
    output_keys: Sequence[str],
    outputs_a: Sequence[Mapping[str, float]],
    outputs_b: Sequence[Mapping[str, float]],
    outputs_ab: Sequence[Sequence[Mapping[str, float]]],
) -> dict[str, Any]:
    """Sobol first-order and total-order indices from precomputed outputs.

    ``outputs_ab[i]`` holds the outputs of the crossed matrix AB_i (A with
    parameter ``parameters[i]`` replaced by B). Each output is centered by
    the mean of all provided outputs (A, B, and every AB block) before
    estimation: the Sobol' (1993) first-order estimator
    ``mean(B * (AB - A)) / V`` is biased for non-centered outputs, and
    centering removes that bias (the same normalization SALib applies).
    Total order uses the Jansen (1999) estimator ``mean((A - AB)^2) / (2V)``;
    ``V`` is the population variance (ddof=0) of the pooled A and B outputs.
    The estimator pair matches SALib's defaults. Extracted as a pure core so
    the estimators can be cross-validated against SALib
    (tests/test_gsa_crosscheck.py).
    """
    samples = len(outputs_a)
    centered: dict[str, tuple[list[float], list[float], list[list[float]]]] = {}
    for key in output_keys:
        pooled = (
            [row[key] for row in outputs_a]
            + [row[key] for row in outputs_b]
            + [row[key] for block in outputs_ab for row in block]
        )
        center = statistics.fmean(pooled)
        centered[key] = (
            [row[key] - center for row in outputs_a],
            [row[key] - center for row in outputs_b],
            [[row[key] - center for row in block] for block in outputs_ab],
        )
    results: dict[str, Any] = {}
    for position, name in enumerate(parameters):
        results[name] = {}
        for key in output_keys:
            values_a, values_b, blocks = centered[key]
            crossed = blocks[position]
            variance = statistics.pvariance(values_a + values_b)
            if variance == 0.0:
                results[name][key] = {"first_order": 0.0, "total": 0.0}
                continue
            first_order = (
                statistics.fmean(
                    values_b[index] * (crossed[index] - values_a[index])
                    for index in range(samples)
                )
                / variance
            )
            total = statistics.fmean(
                (values_a[index] - crossed[index]) ** 2 for index in range(samples)
            ) / (2.0 * variance)
            results[name][key] = {
                "first_order": first_order,
                "total": total,
            }
    return results


def sobol_indices(
    parameters: Sequence[str],
    seeds: Sequence[int],
    periods: int,
    output_keys: Sequence[str],
    base_config: ModelConfig | None = None,
    samples: int = 64,
    design_seed: int = GSA_DESIGN_SEED,
) -> dict[str, Any]:
    """Saltelli/Sobol first-order and total-order variance-based indices.

    Uses the Jansen/Saltelli estimators with A, B, and AB_i matrices; cost is
    ``samples * (len(parameters) + 2)`` model evaluations per seed.
    """
    if periods < 1:
        raise ValueError("periods must be at least 1")
    if samples < 4:
        raise ValueError("samples must be at least 4")
    base = base_config or ModelConfig()
    bounds = {name: _bounds_for(base, name) for name in parameters}
    rng = random.Random(design_seed)

    def sample_row() -> dict[str, float]:
        return {
            name: rng.uniform(bounds[name][0], bounds[name][1]) for name in parameters
        }

    def evaluate(row: Mapping[str, float]) -> dict[str, float]:
        return mean_outputs(
            _config_for_point(base, parameters, row),
            seeds,
            periods,
            output_keys,
        )

    matrix_a = [sample_row() for _ in range(samples)]
    matrix_b = [sample_row() for _ in range(samples)]
    outputs_a = [evaluate(row) for row in matrix_a]
    outputs_b = [evaluate(row) for row in matrix_b]
    outputs_ab: list[list[dict[str, float]]] = []
    for name in parameters:
        crossed = [dict(row) for row in matrix_a]
        for index, row_b in enumerate(matrix_b):
            crossed[index][name] = row_b[name]
        outputs_ab.append([evaluate(row) for row in crossed])
    results = sobol_indices_from_outputs(
        parameters, output_keys, outputs_a, outputs_b, outputs_ab
    )
    return {
        "parameters": list(parameters),
        "samples": samples,
        "bounds": {name: list(bounds[name]) for name in parameters},
        "indices": results,
    }


def history_matching(
    parameters: Sequence[str] = HM_PARAMETERS,
    seeds: Sequence[int] = (1, 2),
    periods: int = 20,
    base_config: ModelConfig | None = None,
    levels: int = HM_LEVELS,
    cutoff: float = HM_CUTOFF,
) -> dict[str, Any]:
    """History-matching pilot: rule out parameter points outside wide bands.

    Each grid point runs every seed; implausibility is the band distance in
    units of seed dispersion (floored), maximized over targets. Points above
    ``cutoff`` are ruled out; the rest are not-ruled-out-yet (NROY).
    Deterministic for fixed seeds; cost is ``levels**len(parameters)`` grid
    points times ``len(seeds)`` model evaluations.
    """
    if periods < 1:
        raise ValueError("periods must be at least 1")
    if levels < 2:
        raise ValueError("levels must be at least 2")
    if not seeds:
        raise ValueError("seeds must not be empty")
    base = base_config or ModelConfig()
    bounds = {name: _bounds_for(base, name) for name in parameters}
    grid = {
        name: [low + k * (high - low) / (levels - 1) for k in range(levels)]
        for name, (low, high) in bounds.items()
    }
    points: list[dict[str, Any]] = []
    evaluations = 0
    for combination in product(*(grid[name] for name in parameters)):
        values = dict(zip(parameters, combination, strict=True))
        config = _config_for_point(base, parameters, values)
        per_seed: dict[str, list[float]] = {
            metric: [] for metric, _, _, _ in HM_TARGETS
        }
        for seed in seeds:
            model = TechnologyParkModel(config=replace(config, seed=seed))
            record: Mapping[str, Any] = cast(Mapping[str, Any], model.metrics())
            for _ in range(periods):
                record = cast(Mapping[str, Any], model.advance())
            evaluations += 1
            for metric, _, _, _ in HM_TARGETS:
                per_seed[metric].append(float(record[metric]))
        details: dict[str, Any] = {}
        implausibility = 0.0
        for metric, low, high, floor in HM_TARGETS:
            mean = statistics.fmean(per_seed[metric])
            spread = statistics.pstdev(per_seed[metric]) if len(seeds) > 1 else 0.0
            if mean < low:
                distance = (low - mean) / math.sqrt(spread**2 + floor**2)
            elif mean > high:
                distance = (mean - high) / math.sqrt(spread**2 + floor**2)
            else:
                distance = 0.0
            details[metric] = {"mean": mean, "sd": spread, "implausibility": distance}
            implausibility = max(implausibility, distance)
        points.append(
            {
                "parameters": dict(values),
                "outputs": details,
                "implausibility": implausibility,
                "ruled_out": implausibility > cutoff,
            }
        )
    not_ruled_out = [point["parameters"] for point in points if not point["ruled_out"]]
    return {
        "parameters": list(parameters),
        "levels": levels,
        "bounds": {name: list(bounds[name]) for name in parameters},
        "targets": [
            {"metric": metric, "low": low, "high": high}
            for metric, low, high, _ in HM_TARGETS
        ],
        "cutoff": cutoff,
        "seeds": list(seeds),
        "periods": periods,
        "evaluations": evaluations,
        "ruled_out_count": sum(1 for point in points if point["ruled_out"]),
        "not_ruled_out_count": len(not_ruled_out),
        "points": points,
        "not_ruled_out": not_ruled_out,
    }


def seed_convergence(
    output_key: str,
    periods: int,
    seed_counts: Sequence[int] = (5, 10, 20, 40),
    base_config: ModelConfig | None = None,
) -> list[dict[str, float]]:
    """Mean and dispersion of a final output as the seed count grows."""
    if periods < 1:
        raise ValueError("periods must be at least 1")
    base = base_config or ModelConfig()
    series: list[dict[str, float]] = []
    for count in seed_counts:
        seeds = tuple(range(1, count + 1))
        values: list[float] = []
        for seed in seeds:
            model = TechnologyParkModel(config=replace(base, seed=seed))
            record: Mapping[str, Any] = cast(Mapping[str, Any], model.metrics())
            for _ in range(periods):
                record = cast(Mapping[str, Any], model.advance())
            values.append(float(record[output_key]))
        series.append(
            {
                "seeds": float(count),
                "mean": statistics.fmean(values),
                "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
            }
        )
    return series


def build_report(
    parameters: Sequence[str],
    factors: Sequence[float],
    seeds: Sequence[int],
    periods: int,
    output_keys: Sequence[str],
    base_config: ModelConfig | None = None,
) -> dict[str, Any]:
    """Build a sensitivity report with manifest metadata."""
    base = base_config or ModelConfig()
    result = one_at_a_time(parameters, factors, seeds, periods, output_keys, base)
    return {
        "schema_version": "1.0",
        "created_utc": datetime.now(UTC).isoformat(),
        "notice": "Simulation sensitivity output; not empirical evidence.",
        "seeds": list(seeds),
        "periods": periods,
        "output_keys": list(output_keys),
        "parameters": list(parameters),
        "factors": list(factors),
        "base_config": asdict(base),
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
        **result,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="One-at-a-time sensitivity analysis for the model."
    )
    parser.add_argument(
        "--parameters",
        nargs="+",
        default=list(DEFAULT_PARAMETERS),
    )
    parser.add_argument(
        "--factors",
        type=float,
        nargs="+",
        default=list(DEFAULT_FACTORS),
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--periods", type=int, default=60)
    parser.add_argument(
        "--interaction",
        nargs=4,
        metavar=("PARAM_A", "VALUE_A", "PARAM_B", "VALUE_B"),
        default=None,
        help="Add a two-way interaction probe for two parameters.",
    )
    parser.add_argument(
        "--gsa",
        choices=["morris", "sobol"],
        default=None,
        help="Add a global sensitivity analysis (Morris screening or Sobol indices).",
    )
    parser.add_argument("--gsa-samples", type=int, default=64)
    parser.add_argument(
        "--gsa-parameters",
        nargs="+",
        default=list(GSA_PARAMETERS),
    )
    parser.add_argument(
        "--convergence",
        action="store_true",
        help="Add a seed-convergence study for knowledge_total and active startups.",
    )
    parser.add_argument(
        "--history-matching",
        action="store_true",
        help="Add a history-matching pilot on the dominant parameters.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / "sensitivity.json",
    )
    args = parser.parse_args(argv)
    if args.periods < 1:
        parser.error("--periods must be at least 1")
    report = build_report(
        tuple(args.parameters),
        tuple(args.factors),
        tuple(args.seeds),
        args.periods,
        DEFAULT_OUTPUT_KEYS,
    )
    if args.interaction is not None:
        name_a, raw_a, name_b, raw_b = args.interaction
        report["interaction"] = two_way_interaction(
            name_a,
            float(raw_a),
            name_b,
            float(raw_b),
            tuple(args.seeds),
            args.periods,
            DEFAULT_OUTPUT_KEYS,
        )
    gsa_parameters = tuple(args.gsa_parameters)
    if args.gsa == "morris":
        report["morris"] = morris_screen(
            gsa_parameters,
            tuple(args.seeds),
            args.periods,
            DEFAULT_OUTPUT_KEYS,
        )
    elif args.gsa == "sobol":
        report["sobol"] = sobol_indices(
            gsa_parameters,
            tuple(args.seeds),
            args.periods,
            DEFAULT_OUTPUT_KEYS,
            samples=args.gsa_samples,
        )
    if args.convergence:
        report["convergence"] = {
            key: seed_convergence(key, args.periods)
            for key in ("knowledge_total", "active_startup_count")
        }
    if args.history_matching:
        report["history_matching"] = history_matching(
            HM_PARAMETERS, tuple(args.seeds), args.periods
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
