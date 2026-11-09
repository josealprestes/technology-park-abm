"""Download cataloged public data sources recorded in data/manifest.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from technology_park_abm.data_contracts import validate_sidra_payload
from technology_park_abm.data_pipeline import (
    CATALOG_PATH,
    accessed_now,
    download_source,
    load_catalog,
    record_download,
    save_catalog,
    sha256_file,
)


def _validate_response(entry: dict[str, object], path: Path) -> None:
    """Reject API error payloads (for example World Bank error messages)."""
    if not str(entry.get("name", "")).startswith("worldbank"):
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("unexpected World Bank payload shape")
    first = payload[0]
    if isinstance(first, dict) and "message" in first:
        message = first["message"][0].get("value", "unknown")
        raise ValueError(f"World Bank API error: {message}")
    observations = payload[1] if len(payload) > 1 else []
    if not isinstance(observations, list) or not observations:
        raise ValueError("World Bank payload has no observations")
    if not any(
        isinstance(observation, dict) and observation.get("value") is not None
        for observation in observations
    ):
        raise ValueError("World Bank payload has no non-null observations")


def _validate_sidra(entry: dict[str, object], path: Path) -> None:
    """Reject malformed SIDRA /values/ payloads (IBGE aggregate sources)."""
    if not str(entry.get("name", "")).startswith("ibge_"):
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_sidra_payload(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--include-downloaded", action="store_true")
    args = parser.parse_args(argv)
    sources = load_catalog(args.catalog)
    selected = [
        entry
        for entry in sources
        if (not args.source or entry["name"] in args.source)
        and (args.include_downloaded or entry["status"] != "downloaded")
    ]
    if not selected:
        print("no sources selected")
        return 0
    failures = 0
    for entry in selected:
        if entry["status"] == "catalog-only":
            print(f"skipping catalog-only source: {entry['name']}")
            continue
        try:
            path = download_source(entry)
            _validate_response(entry, path)
            _validate_sidra(entry, path)
        except Exception as error:  # noqa: BLE001
            print(f"failed: {entry['name']}: {error}", file=sys.stderr)
            failures += 1
            continue
        checksum = sha256_file(path)
        record_download(
            sources,
            entry["name"],
            sha256=checksum,
            accessed_utc=accessed_now(),
        )
        print(f"downloaded {entry['name']} -> {path} sha256={checksum[:12]}...")
    save_catalog(sources, args.catalog)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
