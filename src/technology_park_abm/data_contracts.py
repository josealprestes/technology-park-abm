"""Machine-checkable data contracts for the empirical pipeline.

Three artifacts cross the pipeline boundary (docs/data-contracts.md):

- catalog entries (``data/manifest.json``, schema 1.1): every source must
  declare its legal basis and whether it carries personal data (ADR 0012);
- canonical microdata extracts (CSV with ``education, age, wage, skill``):
  row-level ranges are enforced before resampling
  (``empirical.load_microdata``);
- aggregate series (``year``/``value`` records) and raw SIDRA payloads:
  shape checks run right after download in ``scripts/fetch_public_data.py``
  so a truncated or error payload never reaches ``data/raw``.

Validation only; this module performs no network access and the simulation
never imports it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

CATALOG_SCHEMA_VERSION = "1.1"

REQUIRED_CATALOG_FIELDS: tuple[str, ...] = (
    "name",
    "description",
    "url",
    "license",
    "filename",
    "status",
    "legal_basis",
    "personal_data",
)

CATALOG_STATUSES: tuple[str, ...] = ("cataloged", "catalog-only", "downloaded")
DOWNLOADABLE_STATUSES: frozenset[str] = frozenset({"cataloged", "downloaded"})

# Granularity of the source with respect to personal data (LGPD art. 5th, I):
# "none" = no personal data (macro indicators, legal-entity registries);
# "aggregated" = published statistical aggregates (SIDRA, World Bank);
# "personal" = person-level records (RAIS/CAGED worker microdata).
PERSONAL_DATA_LEVELS: tuple[str, ...] = ("none", "aggregated", "personal")

EDUCATION_LEVELS: tuple[str, ...] = ("fundamental", "medio", "superior")
MICRODATA_AGE_RANGE: tuple[int, int] = (18, 64)

# SIDRA suppresses unstable estimates with "..." and marks not-applicable
# cells with "-"; both are valid payload values and map to None downstream.
SIDRA_SUPPRESSED_VALUES: frozenset[str] = frozenset({"...", "-", "..", "X"})


def validate_catalog_entry(entry: Mapping[str, Any]) -> None:
    """Validate one catalog entry against the schema 1.1 contract.

    Raises ValueError with a specific message on the first violation.
    """
    for field in REQUIRED_CATALOG_FIELDS:
        if field not in entry:
            raise ValueError(f"source {entry.get('name')!r} missing {field!r}")
    name = entry["name"]
    if not isinstance(name, str) or not name:
        raise ValueError("source name must be a non-empty string")
    if not isinstance(entry["url"], str) or not entry["url"]:
        raise ValueError(f"source {name!r} url must be a non-empty string")
    if not isinstance(entry["license"], str) or not entry["license"]:
        raise ValueError(f"source {name!r} license must be a non-empty string")
    if not isinstance(entry["legal_basis"], str) or not entry["legal_basis"]:
        raise ValueError(f"source {name!r} legal_basis must be a non-empty string")
    if entry["personal_data"] not in PERSONAL_DATA_LEVELS:
        raise ValueError(
            f"source {name!r} personal_data must be one of {PERSONAL_DATA_LEVELS}"
        )
    if entry["status"] not in CATALOG_STATUSES:
        raise ValueError(f"source {name!r} has unknown status {entry['status']!r}")
    if entry["status"] in DOWNLOADABLE_STATUSES and not isinstance(
        entry["filename"], str
    ):
        raise ValueError(f"source {name!r} filename must be a string")
    if entry["personal_data"] == "personal" and entry["status"] == "downloaded":
        raise ValueError(
            f"source {name!r} carries personal data and must stay catalog-only "
            "(ADR 0012)"
        )


def validate_microdata_row(row: Mapping[str, str], *, line: int) -> None:
    """Validate one canonical microdata row (education, age, wage, skill)."""
    education = str(row.get("education", "")).strip()
    if education not in EDUCATION_LEVELS:
        raise ValueError(f"microdata line {line}: invalid education {education!r}")
    try:
        age = int(float(str(row.get("age", "")).strip()))
    except ValueError:
        raise ValueError(f"microdata line {line}: age is not a number") from None
    if not MICRODATA_AGE_RANGE[0] <= age <= MICRODATA_AGE_RANGE[1]:
        raise ValueError(
            f"microdata line {line}: age {age} out of range {MICRODATA_AGE_RANGE}"
        )
    try:
        wage = float(str(row.get("wage", "")).strip())
    except ValueError:
        raise ValueError(f"microdata line {line}: wage is not a number") from None
    if not wage > 0:
        raise ValueError(f"microdata line {line}: wage must be positive")
    try:
        skill = float(str(row.get("skill", "")).strip())
    except ValueError:
        raise ValueError(f"microdata line {line}: skill is not a number") from None
    if not 0.0 <= skill <= 1.0:
        raise ValueError(f"microdata line {line}: skill {skill} out of [0, 1]")


def validate_microdata_rows(rows: Sequence[Mapping[str, str]]) -> None:
    """Validate every row of a canonical microdata extract."""
    if not rows:
        raise ValueError("microdata file has no rows")
    for index, row in enumerate(rows, start=2):  # line 1 is the header
        validate_microdata_row(row, line=index)


def validate_sidra_payload(payload: Any) -> None:
    """Validate a raw SIDRA ``/values/`` response (flat JSON array).

    The first element is the header row; data rows carry the value (``V``)
    and the period (``D3N``). Suppressed values ("...", "-") are accepted
    but at least one concrete value must be present.
    """
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError(
            "SIDRA payload must be a JSON array with a header row and data rows"
        )
    header = payload[0]
    if not isinstance(header, dict) or "V" not in header or "D1N" not in header:
        raise ValueError("SIDRA payload header row is malformed")
    concrete = 0
    for row in payload[1:]:
        if not isinstance(row, dict) or "V" not in row or "D3N" not in row:
            raise ValueError("SIDRA payload data row is malformed")
        if str(row["V"]) not in SIDRA_SUPPRESSED_VALUES:
            concrete += 1
    if concrete == 0:
        raise ValueError("SIDRA payload has no non-suppressed values")


def validate_aggregate_series(records: Sequence[Mapping[str, Any]]) -> None:
    """Validate processed year/value records (World Bank, SIDRA extracts).

    ``value`` may be None when the source suppresses the estimate.
    """
    if not records:
        raise ValueError("aggregate series is empty")
    for record in records:
        year = record.get("year")
        if not isinstance(year, int) or isinstance(year, bool):
            raise ValueError(f"aggregate record has invalid year: {year!r}")
        value = record.get("value")
        if value is not None and not isinstance(value, (int, float)):
            raise ValueError(f"aggregate record has invalid value: {value!r}")
