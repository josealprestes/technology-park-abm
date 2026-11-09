# ADR 0004: Data policy for the empirical phase

- Status: accepted
- Date: 2026-10-06

## Context

Phase F7 acquires public data (firm registries, patents and publications, investment databases, employment statistics, technology-transfer records, park administrative data) for calibration and historical validation. `AGENTS.md` forbids committing credentials, tokens, private datasets, or generated secrets. Brazilian personal data is subject to LGPD.

## Decision

- Acquire public sources only. Every source is recorded in `data/manifest.json` with: source name, URL, license or terms, access date, retrieval script, and SHA-256 checksum of the downloaded file.
- Raw and intermediate data live under `data/raw/` and `data/processed/`, both gitignored. Only retrieval and processing scripts, manifests, and checksums are versioned.
- Minimize personal data: prefer aggregated or firm-level records; never store personal identifiers; document legal basis and retention when personal data is unavoidable.
- Calibration starts only after F1-F3 mechanisms and metrics are frozen (metrics contract v1).
- No credentials in the repository; authenticated sources are out of scope, and any future need requires a new ADR.

## Consequences

- F7 deliverables are reproducible scripts plus manifests, not datasets.
- Results depending on data carry the source manifest and uncertainty notes.
