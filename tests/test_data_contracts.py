"""Tests for the data contracts (docs/data-contracts.md, ADR 0012)."""

from __future__ import annotations

import pytest

from technology_park_abm.data_contracts import (
    CATALOG_SCHEMA_VERSION,
    PERSONAL_DATA_LEVELS,
    SIDRA_SUPPRESSED_VALUES,
    validate_aggregate_series,
    validate_catalog_entry,
    validate_microdata_row,
    validate_microdata_rows,
    validate_sidra_payload,
)


def valid_entry() -> dict[str, object]:
    return {
        "name": "example",
        "description": "example source",
        "url": "https://example.org/data",
        "license": "CC BY 4.0",
        "filename": "example.json",
        "status": "cataloged",
        "legal_basis": "Open data (Decreto 8.777/2016)",
        "personal_data": "aggregated",
    }


def test_catalog_schema_version_is_1_1() -> None:
    assert CATALOG_SCHEMA_VERSION == "1.1"


def test_valid_catalog_entry_passes() -> None:
    validate_catalog_entry(valid_entry())


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "description",
        "url",
        "license",
        "filename",
        "status",
        "legal_basis",
        "personal_data",
    ],
)
def test_catalog_entry_missing_field_is_rejected(field: str) -> None:
    entry = valid_entry()
    del entry[field]
    with pytest.raises(ValueError, match=field):
        validate_catalog_entry(entry)


def test_catalog_entry_rejects_empty_legal_basis() -> None:
    entry = valid_entry()
    entry["legal_basis"] = ""
    with pytest.raises(ValueError, match="legal_basis"):
        validate_catalog_entry(entry)


def test_catalog_entry_rejects_unknown_personal_data_level() -> None:
    entry = valid_entry()
    entry["personal_data"] = "pseudonymized"
    with pytest.raises(ValueError, match="personal_data"):
        validate_catalog_entry(entry)


def test_catalog_entry_rejects_unknown_status() -> None:
    entry = valid_entry()
    entry["status"] = "archived"
    with pytest.raises(ValueError, match="status"):
        validate_catalog_entry(entry)


def test_catalog_entry_requires_filename_when_downloadable() -> None:
    entry = valid_entry()
    entry["filename"] = None
    with pytest.raises(ValueError, match="filename"):
        validate_catalog_entry(entry)


def test_personal_data_source_cannot_be_downloaded() -> None:
    entry = valid_entry()
    entry["personal_data"] = "personal"
    entry["status"] = "downloaded"
    with pytest.raises(ValueError, match="ADR 0012"):
        validate_catalog_entry(entry)
    entry["status"] = "catalog-only"
    entry["filename"] = None
    validate_catalog_entry(entry)


def test_personal_data_levels_are_documented() -> None:
    assert PERSONAL_DATA_LEVELS == ("none", "aggregated", "personal")


def test_valid_microdata_row_passes() -> None:
    validate_microdata_row(
        {"education": "superior", "age": "40", "wage": "6.5", "skill": "0.9"},
        line=2,
    )


@pytest.mark.parametrize(
    "row",
    [
        {"education": "doctorado", "age": "40", "wage": "6.5", "skill": "0.9"},
        {"education": "medio", "age": "17", "wage": "2.0", "skill": "0.5"},
        {"education": "medio", "age": "65", "wage": "2.0", "skill": "0.5"},
        {"education": "medio", "age": "abc", "wage": "2.0", "skill": "0.5"},
        {"education": "medio", "age": "30", "wage": "0", "skill": "0.5"},
        {"education": "medio", "age": "30", "wage": "-1", "skill": "0.5"},
        {"education": "medio", "age": "30", "wage": "x", "skill": "0.5"},
        {"education": "medio", "age": "30", "wage": "2.0", "skill": "1.5"},
        {"education": "medio", "age": "30", "wage": "2.0", "skill": "-0.1"},
        {"education": "medio", "age": "30", "wage": "2.0", "skill": "x"},
    ],
)
def test_invalid_microdata_rows_are_rejected(row: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="line 7"):
        validate_microdata_row(row, line=7)


def test_validate_microdata_rows_reports_line_numbers() -> None:
    rows = [
        {"education": "medio", "age": "30", "wage": "2.0", "skill": "0.5"},
        {"education": "medio", "age": "300", "wage": "2.0", "skill": "0.5"},
    ]
    with pytest.raises(ValueError, match="line 3"):
        validate_microdata_rows(rows)


def test_validate_microdata_rows_rejects_empty() -> None:
    with pytest.raises(ValueError, match="no rows"):
        validate_microdata_rows([])


def sidra_payload(values: list[str]) -> list[dict[str, str]]:
    header = {"NC": "Nível Territorial (Código)", "V": "Valor", "D1N": "Brasil"}
    rows = [{"NC": "1", "V": value, "D1N": "Brasil", "D3N": "2025"} for value in values]
    return [header, *rows]


def test_valid_sidra_payload_passes() -> None:
    validate_sidra_payload(sidra_payload(["100.0", "...", "-"]))


def test_sidra_payload_rejects_error_shapes() -> None:
    with pytest.raises(ValueError, match="array"):
        validate_sidra_payload({"statusCode": 500})
    with pytest.raises(ValueError, match="array"):
        validate_sidra_payload([{"V": "Valor"}])
    with pytest.raises(ValueError, match="header"):
        validate_sidra_payload([{"NC": "1"}, {"V": "1", "D3N": "2025"}])
    with pytest.raises(ValueError, match="data row"):
        validate_sidra_payload(
            [{"V": "Valor", "D1N": "Brasil"}, {"NC": "1", "D3N": "2025"}]
        )


def test_sidra_payload_rejects_all_suppressed_values() -> None:
    with pytest.raises(ValueError, match="non-suppressed"):
        validate_sidra_payload(sidra_payload(["...", "-"]))


def test_sidra_suppressed_values_cover_documented_sentinels() -> None:
    assert {"...", "-"} <= SIDRA_SUPPRESSED_VALUES


def test_valid_aggregate_series_passes() -> None:
    validate_aggregate_series(
        [
            {"year": 2023, "value": 1.5},
            {"year": 2024, "value": None},
            {"year": 2025, "value": 2},
        ]
    )


@pytest.mark.parametrize(
    "records",
    [
        [],
        [{"year": "2023", "value": 1.5}],
        [{"year": 2023.5, "value": 1.5}],
        [{"year": True, "value": 1.5}],
        [{"year": 2023, "value": "high"}],
    ],
)
def test_invalid_aggregate_series_is_rejected(records: list[dict[str, object]]) -> None:
    with pytest.raises(ValueError):
        validate_aggregate_series(records)
