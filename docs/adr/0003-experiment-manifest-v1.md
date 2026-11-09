# ADR 0003: Experiment manifest schema v1

- Status: accepted
- Date: 2026-10-06

## Context

`docs/architecture.md` and `docs/experiments.md` require every run to record parameters, seed, initial population, implementation version, and metric schema, and to report distributions rather than a single trajectory. A fixed manifest schema makes runs auditable and reproducible.

## Decision

Every experiment run writes a JSON manifest alongside its outputs (default location `results/`, which is gitignored):

```json
{
  "schema_version": "1.0",
  "run_id": "e1-baseline-<timestamp>-<short-hash>",
  "created_utc": "<ISO-8601 UTC>",
  "experiment": {
    "id": "E1",
    "scenario": "baseline",
    "parameters": {},
    "seeds": [1, 2, 3]
  },
  "model": {
    "package_version": "0.1.0",
    "metric_schema_version": "1.0",
    "git_commit": "<sha>",
    "git_dirty": false
  },
  "environment": {
    "python": "3.12.x",
    "mesa": "3.5.x",
    "platform": "<system>"
  },
  "outputs": {
    "metrics": "metrics.csv",
    "summary": "summary.json"
  }
}
```

Rules:

- `seeds` lists every seed used; `parameters` contains the full effective configuration, including defaults.
- Multi-scenario suites may replace `scenario`/`parameters` with a `scenarios` mapping from scenario name to full parameters, add the run horizon as `periods`, and include a `notice` labeling the output as simulation, never empirical evidence.
- `git_commit` and `git_dirty` identify the exact code state; a dirty tree is allowed for exploration but must be flagged.
- Metric files store one step record per row (or JSONL record) with `period` and a run/seed identifier.
- Summary files store distributions (count, mean, quantiles, min, max) across seeds, never only a final trajectory.
- The same manifest parameters, seeds, and commit must reproduce identical metrics; a small-scale regression test enforces this from F4 onward.

## Consequences

- The runner (F4) is the only component that writes manifests, reusing one implementation to avoid schema drift.
- Manifests are small and may be attached to reports even though `results/` is gitignored.
