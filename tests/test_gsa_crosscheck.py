"""Cross-validation of the GSA estimator cores against SALib.

SALib is a dev-only dependency (pyproject.toml): it is the reference
implementation for Morris screening and Sobol variance-based indices. These
tests feed the same designs and outputs to our pure estimator cores
(`morris_effect_stats`, `sobol_indices_from_outputs`) and to SALib's
analyzers, and require agreement to machine precision. They validate the
estimator math; the model-facing wrappers are covered by determinism and
structure tests in tests/test_sensitivity.py.
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip("SALib")

import numpy as np
from SALib.analyze import morris as salib_morris_analyze
from SALib.analyze import sobol as salib_sobol_analyze
from SALib.sample import sobol as salib_sobol_sample
from SALib.sample.morris.morris import sample as salib_morris_sample
from SALib.test_functions import Ishigami

from technology_park_abm.sensitivity import (
    morris_effect_stats,
    sobol_indices_from_outputs,
)

TOLERANCE = 1e-9
CROSSCHECK_SEED = 20261022


def test_sobol_indices_match_salib_on_ishigami() -> None:
    problem = {
        "num_vars": 3,
        "names": ["x1", "x2", "x3"],
        "bounds": [[-math.pi, math.pi]] * 3,
    }
    samples, num_vars = 64, 3
    design = salib_sobol_sample.sample(
        problem, samples, calc_second_order=False, seed=CROSSCHECK_SEED
    )
    outputs = Ishigami.evaluate(design)
    # SALib interleaves the matrices per sample index: each block of
    # (num_vars + 2) rows is [A_i, AB_1_i, ..., AB_D_i, B_i].
    step = num_vars + 2
    matrix_a = design[0::step]
    matrix_b = design[step - 1 :: step]
    matrices_ab = [design[j + 1 :: step] for j in range(num_vars)]
    rows_a = [{"y": float(value)} for value in Ishigami.evaluate(matrix_a)]
    rows_b = [{"y": float(value)} for value in Ishigami.evaluate(matrix_b)]
    rows_ab = [
        [{"y": float(value)} for value in Ishigami.evaluate(matrix)]
        for matrix in matrices_ab
    ]
    ours = sobol_indices_from_outputs(
        ["x1", "x2", "x3"], ["y"], rows_a, rows_b, rows_ab
    )
    theirs = salib_sobol_analyze.analyze(  # type: ignore[no-untyped-call]
        problem, outputs, calc_second_order=False, print_to_console=False
    )
    for index, name in enumerate(["x1", "x2", "x3"]):
        assert ours[name]["y"]["first_order"] == pytest.approx(
            theirs["S1"][index], abs=TOLERANCE
        )
        assert ours[name]["y"]["total"] == pytest.approx(
            theirs["ST"][index], abs=TOLERANCE
        )


def test_sobol_indices_are_zero_for_constant_output() -> None:
    rows = [{"y": 1.0}] * 8
    ours = sobol_indices_from_outputs(["x1"], ["y"], rows, rows, [rows])
    assert ours["x1"]["y"] == {"first_order": 0.0, "total": 0.0}


def test_morris_stats_match_salib() -> None:
    problem = {
        "num_vars": 2,
        "names": ["x1", "x2"],
        "bounds": [[0.0, 1.0], [0.0, 1.0]],
    }
    design = salib_morris_sample(problem, 6, num_levels=4, seed=CROSSCHECK_SEED)
    design = np.asarray(design)
    outputs = design[:, 0] + 2.0 * design[:, 1] + 0.5 * design[:, 0] * design[:, 1]
    theirs = salib_morris_analyze.analyze(
        problem, design, outputs, num_levels=4, print_to_console=False
    )
    # Elementary effects from the design: within each trajectory block of
    # (num_vars + 1) rows, consecutive rows differ in exactly one parameter;
    # EE = delta output / delta input for that parameter.
    num_vars = 2
    trajectories = design.shape[0] // (num_vars + 1)
    effects: dict[str, list[float]] = {"x1": [], "x2": []}
    for trajectory in range(trajectories):
        block = design[trajectory * (num_vars + 1) : (trajectory + 1) * (num_vars + 1)]
        block_outputs = outputs[
            trajectory * (num_vars + 1) : (trajectory + 1) * (num_vars + 1)
        ]
        for step_index in range(num_vars):
            difference = block[step_index + 1] - block[step_index]
            changed = int(np.nonzero(difference)[0][0])
            effect = (
                block_outputs[step_index + 1] - block_outputs[step_index]
            ) / difference[changed]
            effects[f"x{changed + 1}"].append(float(effect))
    ours = morris_effect_stats(
        ["x1", "x2"],
        ["y"],
        {"x1": {"y": effects["x1"]}, "x2": {"y": effects["x2"]}},
        {"x1": (0.0, 1.0), "x2": (0.0, 1.0)},
    )
    for index, name in enumerate(["x1", "x2"]):
        assert ours[name]["y"]["mu_star"] == pytest.approx(
            theirs["mu_star"][index], abs=TOLERANCE
        )
        assert ours[name]["y"]["sigma"] == pytest.approx(
            theirs["sigma"][index], abs=TOLERANCE
        )
