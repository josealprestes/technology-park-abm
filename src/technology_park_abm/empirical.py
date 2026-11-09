"""Public-data aggregates and microdata loading for agent attributes.

Aggregate tables below are real published values for Brazil with documented
provenance in ``AGGREGATE_SOURCES`` (RAIS/MTE formal-employment stock and
PNAD Contínua/IBGE work income). Wages are in minimum wages (SM) so bands
stay comparable across years; band midpoints track the published means. The
microdata mode reads a canonical CSV extract that the retrieval pipeline
(docs/data-and-calibration.md) can produce; raw data is never committed
(ADR 0004). Only published aggregates live in this module.
"""

from __future__ import annotations

import csv
import math
import random
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from technology_park_abm.data_contracts import validate_microdata_rows

EMPIRICAL_MODES: tuple[str, ...] = ("none", "aggregates", "microdata")
SECTOR_PROFILE_NAMES: tuple[str, ...] = ("none", "brazil_tech")
CONNECTION_PROFILES: tuple[str, ...] = ("baseline", "empirical")

# Provenance for every aggregate table (access 2026-10-13). Values are
# national formal-employment (RAIS) or occupied-population (PNAD) marginals;
# a technology park would skew more schooled, which stays a documented
# limitation (see docs/empirical-calibration-report.md).
AGGREGATE_SOURCES: dict[str, str] = {
    "education": (
        "RAIS 2023, MTE presentation (formal-employment stock by schooling, "
        "complete RAIS universe, 54.7M vínculos): fundamental 13.77%, medio "
        "55.00%, superior 31.24% (6-level chart grouped into 3 levels)."
    ),
    "age": (
        "RAIS 2023, MTE executive summary (absolute stock by age band), "
        "renormalized over ages 18-64 with uniform splits of the 10-year "
        "bands 30-39, 40-49 and 50-59."
    ),
    "wage": (
        "PNAD Contínua work income means: fundamental R$2,535 and medio "
        "R$2,905 (2025 press release); superior R$6,947 (2025); FGV IBRE "
        "Carta de Conjuntura Oct 2024 (superior R$6,619 vs medio R$2,548 in "
        "2024, +126% premium). Bands in minimum wages centered on these means."
    ),
}

EDUCATION_LEVELS: tuple[str, ...] = ("fundamental", "medio", "superior")
_EDUCATION_SHARES: tuple[float, ...] = (0.138, 0.550, 0.312)
_AGE_BANDS: tuple[tuple[int, int], ...] = (
    (18, 24),
    (25, 34),
    (35, 44),
    (45, 54),
    (55, 64),
)
_AGE_SHARES: tuple[float, ...] = (0.134, 0.279, 0.270, 0.205, 0.112)
_WAGE_BANDS: dict[str, tuple[float, float]] = {
    "fundamental": (1.2, 2.1),
    "medio": (1.4, 2.5),
    "superior": (3.2, 6.0),
}
_SIZE_CLASSES: tuple[str, ...] = ("micro", "small", "medium")
_SIZE_SHARES: tuple[float, ...] = (0.70, 0.25, 0.05)
_RESEARCH_BANDS: tuple[tuple[float, float], ...] = (
    (0.2, 0.5),
    (0.5, 0.8),
    (0.8, 1.0),
)
_RESEARCH_SHARES: tuple[float, ...] = (0.55, 0.35, 0.10)

MICRODATA_COLUMNS: tuple[str, ...] = ("education", "age", "wage", "skill")

SECTOR_PROFILES: dict[str, dict[str, dict[str, float]]] = {
    "brazil_tech": {
        "software": {"entry": 1.25, "exit": 0.90, "hiring": 1.20},
        "hardware": {"entry": 0.85, "exit": 1.10, "hiring": 0.90},
        "biotech": {"entry": 0.90, "exit": 1.00, "hiring": 0.95},
        "energy": {"entry": 0.95, "exit": 1.05, "hiring": 1.00},
    }
}

# Real anchor-firm sample: BrasilAPI CNPJ endpoints, 10 large Brazilian firms,
# accessed 2026-10-07 (see scripts/build_empirical_profiles.py and
# data/manifest.json). Capital is stored in R$ billions; anchor capital is
# informational and does not drive mechanisms. Median 14.2, range 2.96-205.4.
ANCHOR_SAMPLE: dict[str, Any] = {
    "source": "BrasilAPI CNPJ sample (2026-10-07)",
    "capital_min_brl_billions": 2.96,
    "capital_median_brl_billions": 14.2,
    "capital_max_brl_billions": 205.4,
    "age_median_years": 43.0,
}

# Sector proximity prior inspired by CNAE section relatedness (placeholder
# weights, symmetric); used only when connection_profile is "empirical".
SECTOR_PROXIMITY: dict[str, dict[str, float]] = {
    "software": {"software": 1.0, "hardware": 0.6, "energy": 0.3, "biotech": 0.3},
    "hardware": {"software": 0.6, "hardware": 1.0, "energy": 0.4, "biotech": 0.3},
    "energy": {"software": 0.3, "hardware": 0.4, "energy": 1.0, "biotech": 0.4},
    "biotech": {"software": 0.3, "hardware": 0.3, "energy": 0.4, "biotech": 1.0},
}
SECTOR_PROXIMITY_WEIGHT = 0.10
UNIVERSITY_COPATENT_BONUS = 0.10


def _weighted_choice(
    rng: random.Random,
    options: Sequence[Any],
    shares: Sequence[float],
) -> Any:
    return rng.choices(list(options), weights=list(shares), k=1)[0]


def skill_for(education: str, age: int, rng: random.Random) -> float:
    """Worker skill from education and experience plus small noise."""
    base = {"fundamental": 0.30, "medio": 0.50, "superior": 0.70}.get(education, 0.50)
    experience = min(0.20, max(0.0, (age - 18) * 0.005))
    skill = base + experience + rng.uniform(-0.05, 0.05)
    return min(1.0, max(0.05, skill))


def sample_worker(
    rng: random.Random,
    rows: Sequence[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Sample worker attributes, optionally resampling microdata rows."""
    if rows:
        row = rng.choice(list(rows))
        return {
            "education": str(row.get("education", "medio")),
            "age": int(float(row.get("age", 30) or 30)),
            "wage": float(row.get("wage", 2.0) or 2.0),
            "skill": float(row.get("skill", 0.5) or 0.5),
        }
    education = _weighted_choice(rng, EDUCATION_LEVELS, _EDUCATION_SHARES)
    wage_min, wage_max = _WAGE_BANDS[education]
    age_min, age_max = _weighted_choice(rng, _AGE_BANDS, _AGE_SHARES)
    age = rng.randint(age_min, age_max)
    return {
        "education": education,
        "age": age,
        "wage": rng.uniform(wage_min, wage_max),
        "skill": skill_for(education, age, rng),
    }


def sample_size_class(rng: random.Random) -> str:
    return str(_weighted_choice(rng, _SIZE_CLASSES, _SIZE_SHARES))


def sample_research_quality(rng: random.Random) -> float:
    low, high = _weighted_choice(rng, _RESEARCH_BANDS, _RESEARCH_SHARES)
    return rng.uniform(low, high)


def sample_anchor_employees(rng: random.Random) -> int:
    return rng.randint(100, 5000)


def sample_anchor_capital(rng: random.Random) -> float:
    """Log-uniform capital draw from the real sample range (R$ billions)."""
    return 10 ** rng.uniform(
        math.log10(ANCHOR_SAMPLE["capital_min_brl_billions"]),
        math.log10(ANCHOR_SAMPLE["capital_max_brl_billions"]),
    )


def sector_proximity(first: str, second: str) -> float:
    """Symmetric sector proximity in [0, 1]; unknown sectors score 0.0."""
    row = SECTOR_PROXIMITY.get(first)
    if row is None:
        return 0.0
    return float(row.get(second, 0.0))


def load_microdata(path: str | Path) -> list[dict[str, str]]:
    """Load a canonical CSV extract with the documented columns.

    Every row is validated against the microdata contract
    (``data_contracts.validate_microdata_rows``, docs/data-contracts.md).
    """
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"microdata file not found: {source}")
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in MICRODATA_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"microdata missing columns: {missing}")
        rows = [dict(row) for row in reader]
    validate_microdata_rows(rows)
    return rows
