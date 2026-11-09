"""Performance smoke: a long run completes within a generous budget."""

from __future__ import annotations

import time

import pytest

from technology_park_abm import TechnologyParkModel

pytestmark = pytest.mark.e2e

BUDGET_SECONDS = 60.0


def test_long_run_stays_within_budget() -> None:
    model = TechnologyParkModel(seed=42)
    started = time.perf_counter()
    for _ in range(500):
        model.advance()
    elapsed = time.perf_counter() - started
    assert model.metrics()["period"] == 500
    assert elapsed < BUDGET_SECONDS
