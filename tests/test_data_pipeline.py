import json
from pathlib import Path

import pytest

from technology_park_abm.data_pipeline import (
    download_source,
    load_catalog,
    record_download,
    save_catalog,
    sha256_file,
)

REPO_CATALOG = Path("data") / "manifest.json"


def test_catalog_entries_have_required_fields() -> None:
    sources = load_catalog(REPO_CATALOG)
    assert sources
    names = {entry["name"] for entry in sources}
    assert "worldbank_tech_exports_brazil" in names
    for entry in sources:
        assert isinstance(entry["name"], str)
        assert isinstance(entry["url"], str)
        assert isinstance(entry["license"], str)
        assert isinstance(entry["legal_basis"], str) and entry["legal_basis"]
        assert entry["personal_data"] in {"none", "aggregated", "personal"}
        assert entry["status"] in {"cataloged", "catalog-only", "downloaded"}
        if entry["personal_data"] == "personal":
            assert entry["status"] == "catalog-only"


def test_sha256_file_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "sample.bin"
    path.write_bytes(b"technology-park-abm")
    digest = sha256_file(path)
    assert digest == sha256_file(path)
    assert len(digest) == 64


def test_catalog_round_trip(tmp_path: Path) -> None:
    sources: list[dict[str, object]] = [
        {
            "name": "example",
            "description": "example",
            "url": "https://example.org/data",
            "license": "CC0",
            "filename": "example.json",
            "fields": [],
            "status": "cataloged",
            "legal_basis": "Open data (Decreto 8.777/2016)",
            "personal_data": "aggregated",
            "sha256": None,
            "accessed_utc": None,
        }
    ]
    path = tmp_path / "manifest.json"
    save_catalog(sources, path)
    assert load_catalog(path) == sources


def test_record_download_updates_status() -> None:
    sources: list[dict[str, object]] = [
        {
            "name": "example",
            "status": "cataloged",
            "sha256": None,
            "accessed_utc": None,
        }
    ]
    record_download(
        sources,
        "example",
        sha256="abc",
        accessed_utc="2026-10-06T00:00:00+00:00",
    )
    assert sources[0]["status"] == "downloaded"
    assert sources[0]["sha256"] == "abc"
    assert sources[0]["accessed_utc"] == "2026-10-06T00:00:00+00:00"


def test_duplicate_catalog_names_are_rejected(tmp_path: Path) -> None:
    entry = {
        "name": "duplicate",
        "description": "duplicate",
        "url": "https://example.org",
        "license": "CC0",
        "filename": "dup.json",
        "status": "cataloged",
        "legal_basis": "Open data",
        "personal_data": "aggregated",
    }
    path = tmp_path / "dup.json"
    path.write_text(
        json.dumps({"schema_version": "1.1", "sources": [entry, dict(entry)]}),
        encoding="utf-8",
    )
    try:
        load_catalog(path)
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate names should fail")


def test_downloadable_entry_requires_filename(tmp_path: Path) -> None:
    entry = {
        "name": "broken",
        "description": "broken",
        "url": "https://example.org",
        "license": "CC0",
        "filename": None,
        "status": "cataloged",
        "legal_basis": "Open data",
        "personal_data": "aggregated",
    }
    path = tmp_path / "broken.json"
    path.write_text(
        json.dumps({"schema_version": "1.1", "sources": [entry]}),
        encoding="utf-8",
    )
    try:
        load_catalog(path)
    except ValueError:
        pass
    else:
        raise AssertionError("missing filename should fail")


def test_personal_data_source_cannot_be_downloaded(tmp_path: Path) -> None:
    entry = {
        "name": "microdata",
        "description": "worker-level records",
        "url": "https://example.org/microdata",
        "license": "Terms of use",
        "filename": "microdata.txt",
        "status": "downloaded",
        "legal_basis": "Out of scope (ADR 0012)",
        "personal_data": "personal",
    }
    path = tmp_path / "personal.json"
    path.write_text(
        json.dumps({"schema_version": "1.1", "sources": [entry]}),
        encoding="utf-8",
    )
    try:
        load_catalog(path)
    except ValueError:
        pass
    else:
        raise AssertionError("personal-data sources must stay catalog-only")


@pytest.mark.e2e
def test_download_source_respects_size_cap(tmp_path: Path) -> None:
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"1234567890")
    entry = {"name": "local", "url": payload.as_uri(), "filename": "local.bin"}
    destination = download_source(entry, tmp_path / "raw", max_bytes=100)
    assert destination.read_bytes() == b"1234567890"
    try:
        download_source(entry, tmp_path / "raw", max_bytes=5)
    except ValueError:
        pass
    else:
        raise AssertionError("oversized download should fail")


def test_missing_catalog_field_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps({"schema_version": "1.1", "sources": [{"name": "x"}]}),
        encoding="utf-8",
    )
    try:
        load_catalog(path)
    except ValueError:
        pass
    else:
        raise AssertionError("missing fields should fail")


def test_unsupported_schema_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "old.json"
    path.write_text(
        json.dumps({"schema_version": "1.0", "sources": []}), encoding="utf-8"
    )
    try:
        load_catalog(path)
    except ValueError:
        pass
    else:
        raise AssertionError("schema 1.0 catalogs should fail")
