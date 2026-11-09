"""Pytest configuration: test categories.

Tests carrying an explicit category marker (unit, regression, smoke, e2e) keep
it; every other test defaults to ``unit`` so the four requested categories
always partition the suite.
"""

from __future__ import annotations

from typing import Any

import pytest

CATEGORIES = ("unit", "regression", "smoke", "e2e")


def pytest_collection_modifyitems(items: list[Any]) -> None:
    for item in items:
        if any(item.get_closest_marker(name) for name in CATEGORIES):
            continue
        item.add_marker(pytest.mark.unit)
