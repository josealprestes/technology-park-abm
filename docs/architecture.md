# Architecture

## Layers

1. **Agents**: startups, anchor firms, universities, investors, workers, and governance.
2. **Environment**: sectors, infrastructure, labor market, funding conditions, and policy parameters.
3. **Network**: typed and weighted relationships such as partnership, investment, hiring, competition, and knowledge transfer.
4. **Processes**: entry, matching, R&D, knowledge diffusion, market interaction, governance, congestion, and exit.
5. **Measurements**: population, survival, productivity, innovation, investment, employment, network structure, and resilience.

## Proposed step order

1. Admit potential entrants.
2. Update available infrastructure and policy.
3. Form or dissolve network ties.
4. Allocate resources to R&D and market activities.
5. Diffuse knowledge through active ties.
6. Execute investment and hiring.
7. Apply revenue, costs, and congestion.
8. Process exits, acquisitions, and migration.
9. Update collective reputation.
10. Collect metrics and snapshots.

As of F2, all ten steps are implemented; see `docs/model-specification.md` for formulas and limitations.

## Extension points

- Adopt Mesa as decided in `docs/adr/0001-mesa-framework.md`; the hand-rolled skeleton is replaced as the engine in phase F1 of `docs/execution-plan.md`.
- Add typed network edges without coupling them to agent classes.
- Inject policies as strategies rather than hard-coded conditionals.
- Add empirical calibration through configuration files.
- Add experiment runners that persist seed, parameters, code version, and outputs.

## Reproducibility

Every run should record model parameters, random seed, initial population, implementation version, and metric schema.

## Optional investigation workbench (Unreleased)

The released single-file dashboard remains at `static/dashboard.html` and
port 8765. The optional workbench is assembled from `docs/prototypes/` by
`scripts/build_investigation_prototype.py` into a self-contained HTML under
ignored `outputs/`. It embeds seeded examples, fonts and a versioned research
catalog; no external runtime asset or visualization dependency is added.

`scripts/serve_investigation_prototype.py` serves that HTML and a same-origin
job API on loopback port 8777. It owns input-size/origin checks, one active
job, progress, cooperative cancellation and four in-memory job records.
`investigation.py` uses the canonical configuration parser and actual model
for metrics/events; an independent, identically seeded `DashboardSession`
records network frames for the first seed. This duplicates that seed's work
to preserve existing snapshot/layout semantics; it does not change the engine.

Interactive limits are applied by this adapter, not by changing `ModelConfig`.
The model makes no network calls. UI drafts are separate from executed
conditions; editing requires execution before exploration. Replay reads
per-period records, while plots aggregate the selected seeds. Exports are
cursor-scoped and preserve effective configuration, source provenance and
conceptual dossier. Full operation/API and persistence limits are in
[`investigation-workbench.md`](investigation-workbench.md).

The view derives the productive-tie definition from each effective
configuration. If thresholds differ, its raw counts remain visible while
delta/paired verdicts are unavailable for that metric; the model is unchanged.
JSON schema 3 adds measurement comparability metadata. CSV schema 2 includes
p0 and per-row seed-specific configuration/provenance with proper field
quoting, enabling reconstruction without a separate JSON download. Figure
scope and transport-error recovery are also enforced by the workbench browser
tests; see `verification-investigation-fixes-2026-10-25.md`.
