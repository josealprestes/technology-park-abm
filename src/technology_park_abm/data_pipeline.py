"""Public data catalog and retrieval pipeline (ADR 0004, phase F7).

Network access lives only in the download function and is never used by the
simulation itself. Raw data is stored outside version control; the catalog
stores URLs, licenses, legal bases, personal-data levels, access dates, and
SHA-256 checksums. Entry validation follows the schema 1.1 data contract
(``data_contracts.py``, docs/data-contracts.md, ADR 0012).
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from technology_park_abm.data_contracts import (
    CATALOG_SCHEMA_VERSION,
    validate_catalog_entry,
)

CATALOG_PATH = Path("data") / "manifest.json"
RAW_DIR = Path("data") / "raw"
DEFAULT_MAX_DOWNLOAD_BYTES = 50_000_000


def sha256_file(path: Path) -> str:
    """Return the SHA-256 checksum of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_catalog(path: Path = CATALOG_PATH) -> list[dict[str, Any]]:
    """Load and validate the source catalog.

    Default paths are relative to the repository root; run from there.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise ValueError(f"catalog schema_version must be {CATALOG_SCHEMA_VERSION!r}")
    sources = payload["sources"]
    if not isinstance(sources, list):
        raise ValueError("catalog sources must be a list")
    names: set[str] = set()
    for entry in sources:
        validate_catalog_entry(entry)
        name = entry["name"]
        if name in names:
            raise ValueError(f"duplicate source name: {name!r}")
        names.add(name)
    return sources


def save_catalog(sources: list[dict[str, Any]], path: Path = CATALOG_PATH) -> None:
    """Persist the source catalog."""
    payload = {"schema_version": CATALOG_SCHEMA_VERSION, "sources": sources}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def record_download(
    sources: list[dict[str, Any]],
    name: str,
    *,
    sha256: str,
    accessed_utc: str,
) -> dict[str, Any]:
    """Record a checksum and access timestamp for a downloaded source."""
    for entry in sources:
        if entry["name"] == name:
            entry["sha256"] = sha256
            entry["accessed_utc"] = accessed_utc
            entry["status"] = "downloaded"
            return entry
    raise KeyError(f"unknown source: {name}")


def download_source(
    entry: dict[str, Any],
    destination_dir: Path = RAW_DIR,
    timeout: float = 30.0,
    max_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
) -> Path:
    """Download one cataloged source and return the local file path.

    Downloads larger than max_bytes are rejected to avoid accidental huge
    retrievals; raise max_bytes explicitly for legitimately large sources.
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / str(entry["filename"])
    request = urllib.request.Request(
        entry["url"], headers={"User-Agent": "technology-park-abm/1.0"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError(
            f"source exceeds {max_bytes} bytes; raise max_bytes to allow it"
        )
    destination.write_bytes(payload)
    return destination


def accessed_now() -> str:
    """Return the current UTC timestamp in ISO-8601 form."""
    return datetime.now(UTC).isoformat()


def summarize_company_sample(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize a real CNPJ sample: porte shares, capital, and age stats.

    ``rows`` are records returned by public CNPJ APIs; only aggregated
    statistics are produced so nothing personally identifiable is stored.
    """
    companies = [row for row in rows if row]
    if not companies:
        raise ValueError("company sample is empty")
    porte_counts: dict[str, int] = {}
    capitals: list[float] = []
    ages: list[float] = []
    for row in companies:
        porte = str(row.get("porte", "desconhecido") or "desconhecido")
        porte_counts[porte] = porte_counts.get(porte, 0) + 1
        capital = row.get("capital_social")
        if capital is not None:
            capitals.append(float(capital))
        start = row.get("data_inicio_atividade")
        if start:
            start_year = int(str(start)[:4])
            ages.append(float(2026 - start_year))
    capitals.sort()
    ages.sort()
    count = len(companies)

    def quantile(values: list[float], fraction: float) -> float:
        if not values:
            return 0.0
        index = min(len(values) - 1, max(0, round(fraction * (len(values) - 1))))
        return values[index]

    return {
        "count": count,
        "porte_shares": {
            name: value / count for name, value in sorted(porte_counts.items())
        },
        "capital_min": capitals[0] if capitals else 0.0,
        "capital_median": quantile(capitals, 0.5),
        "capital_max": capitals[-1] if capitals else 0.0,
        "age_min": ages[0] if ages else 0.0,
        "age_median": quantile(ages, 0.5),
        "age_max": ages[-1] if ages else 0.0,
    }
