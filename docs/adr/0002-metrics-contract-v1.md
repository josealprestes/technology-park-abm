# ADR 0002: Metrics contract v1

- Status: accepted
- Date: 2026-10-06

## Context

Metrics are the interface between the model and every experiment, validation step, and report. `docs/model-specification.md` requires that metrics distinguish quantity from quality and effective interaction, and that every record identifies the simulation period. Without a fixed contract, metric names and semantics drift across phases.

## Decision

### Step record

Every simulation step produces a mapping (step record) with:

- `period` (int >= 0): increments by exactly one per step. Transitional note (completed in F1): the original skeleton emitted `time`; the Mesa model emits `period`.
- Metric keys using these conventions:
  - `*_count`: non-negative integer counts.
  - `mean_*`: arithmetic means over the relevant living population.
  - `*_rate`: values in [0, 1].
  - `*_by_type`: mapping from a documented categorical key (for example exit type) to a count, always containing all categories.

Units and population scope are documented per metric in `docs/model-specification.md`.

### Baseline keys (current behavior)

- `period`: int
- `startup_count`: int, total startups created in the run
- `active_startup_count`: int, alive startups
- `capital_total`: float >= 0, sum of capital over active startups
- `knowledge_total`: float >= 0, sum of knowledge over active startups

### Invariants

- Counts and stocks are never negative.
- Dead agents contribute nothing to active aggregates.
- Rate metrics stay within [0, 1].
- Identical seed and parameters produce identical step records.
- Every record carries `period`.

### Extension policy

- Within v1, changes are additive: new keys may be added; existing keys never change meaning or type.
- Removal or semantic change requires a new schema version (v2) with an ADR, and the version is recorded in run manifests (ADR 0003).

## Consequences

- F1 renames skeleton keys to the canonical names above without changing behavior.
- F3 adds the full metric suite (ties, knowledge, innovation, exits by type, employment, reputation, density, centralization, congestion) under these conventions.
- Experiment runners and the manifest schema depend on this contract.
