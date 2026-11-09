"""Build empirical anchor profiles from a real public CNPJ sample.

Fetches a fixed list of well-known Brazilian companies from the public
BrasilAPI CNPJ endpoint, computes aggregate statistics (porte shares, capital
and age quantiles), writes them to ``data/processed/`` (gitignored), records
the checksum in ``data/manifest.json``, and prints the summary used to update
the documented constants in ``technology_park_abm.empirical``.

Only aggregated statistics leave this script; no personal data is stored.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from technology_park_abm.data_pipeline import (
    CATALOG_PATH,
    accessed_now,
    load_catalog,
    save_catalog,
    sha256_file,
    summarize_company_sample,
)

SAMPLE_CNPJS: tuple[str, ...] = (
    "84429695000111",  # WEG
    "07689002000189",  # Embraer
    "53113791000122",  # TOTVS
    "47960950000121",  # Magazine Luiza
    "71673990000177",  # Natura
    "33592510000154",  # Vale
    "60701190000104",  # Itau Unibanco
    "07526557000100",  # Ambev
    "16404287000155",  # Suzano
    "33000167000101",  # Petrobras
)
OUTPUT_PATH = Path("data") / "processed" / "anchor_sample.json"
SOURCE_NAME = "brasilapi_cnpj_sample"


def fetch_company(cnpj: str, timeout: float = 20.0) -> dict[str, Any] | None:
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "technology-park-abm/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:  # noqa: BLE001 - report and continue per company
        print(f"failed: {cnpj}: {error}")
        return None
    return {
        "razao_social": payload.get("razao_social"),
        "porte": payload.get("porte"),
        "capital_social": payload.get("capital_social"),
        "data_inicio_atividade": payload.get("data_inicio_atividade"),
        "cnae_fiscal_descricao": payload.get("cnae_fiscal_descricao"),
        "municipio": payload.get("municipio"),
        "uf": payload.get("uf"),
    }


def update_catalog(checksum: str, summary: dict[str, Any]) -> None:
    sources = load_catalog(CATALOG_PATH)
    entries = [entry for entry in sources if entry["name"] == SOURCE_NAME]
    entry: dict[str, Any] = {
        "name": SOURCE_NAME,
        "description": (
            "Aggregated anchor-firm statistics from a real public CNPJ sample "
            "(BrasilAPI): porte shares, capital and age quantiles"
        ),
        "url": "https://brasilapi.com.br/api/cnpj/v1/{cnpj}",
        "license": "Open data (company registry); aggregated output only",
        "filename": "anchor_sample.json",
        "fields": ["porte_shares", "capital_*", "age_*"],
        "status": "downloaded",
        "sha256": checksum,
        "accessed_utc": accessed_now(),
        "summary": summary,
    }
    if entries:
        sources[sources.index(entries[0])] = entry
    else:
        sources.append(entry)
    save_catalog(sources, CATALOG_PATH)


def main() -> int:
    rows: list[dict[str, Any]] = []
    for cnpj in SAMPLE_CNPJS:
        company = fetch_company(cnpj)
        if company:
            rows.append(company)
    summary = summarize_company_sample(rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    checksum = sha256_file(OUTPUT_PATH)
    update_catalog(checksum, summary)
    print(json.dumps(summary, indent=2))
    print(f"sample size: {summary['count']} of {len(SAMPLE_CNPJS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
