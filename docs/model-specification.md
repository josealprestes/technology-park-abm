# Model specification

## Agents

The target model includes startups, anchor firms, universities or ICTs, investors, workers, and a park manager or public authority.

## Startup state

A startup may contain capital, technology quality, knowledge, reputation, team size, sector, age, and access to clients or investors.

## Core mechanisms

### Entry

Entry probability should increase with park reputation, funding availability, research quality, infrastructure, and expected opportunity, while decreasing with operating cost.

### Partnerships

Partnership probability should depend on network opportunity, technological compatibility, complementarity, reputation, and coordination cost.

### Knowledge

Knowledge changes through internal R&D, hiring, active network ties, and depreciation or obsolescence.

### Finance and markets

Cash flow should combine revenue, investment, R&D cost, labor cost, and congestion-related cost.

### Exit

Exit can represent failure, acquisition, voluntary departure, or migration. These events must be distinguished in the data.

### Reputation

Collective reputation should update from historical outcomes and influence subsequent entry, funding, talent attraction, and partnership formation.

## Increasing returns

A useful diagnostic is marginal output per additional effective agent:

`G(N) = delta Y / delta N`

Increasing returns occur when this marginal contribution rises over a range of system size. The model should also include saturation or congestion so that increasing returns are not guaranteed indefinitely.

## Metrics

At minimum collect population, active ties, productive ties, mean knowledge, innovation events, capital, exits by type, employment, reputation, density, centralization, and congestion.

## Invariants

- Capital and population cannot become negative.
- Dead agents cannot create new ties or outputs.
- All random behavior is reproducible with a supplied seed.
- Metrics must identify the simulation period.

## Phase F1 implemented state

The following state is implemented in code as of F1. Values marked as defaults are calibration placeholders, not empirical claims.

### Agent state

| Agent | State variables |
| --- | --- |
| Startup | sector, capital, technology_quality, knowledge, reputation, team_size, age, access_to_clients, access_to_investors, alive |
| AnchorFirm | sector, capital, technology_quality, knowledge, reputation, participation (passive or active) |
| University | research_quality, knowledge_stock, technology_transfer_activity |
| Investor | capital_available, risk_appetite, active |
| Worker | sector (optional), skill, employed_by |
| ParkAuthority | policy, reputation |

### Environment

- SectorSpace holds the ordered sector tuple and same-sector and cross-sector compatibility and complementarity values in [0, 1]. Defaults are same-sector compatibility 1.0, cross-sector compatibility 0.25, and complementarity 0.5 for both, a neutral placeholder for E2 calibration.
- infrastructure_capacity and infrastructure_load are non-negative; load is updated by processes from F2 onward.
- funding_conditions and labor_market_slack are non-negative.
- Policy instruments (entry subsidy, R&D subsidy, shared infrastructure, matchmaking, talent program, investment fund) default to zero.

### Randomness

- A single master seed derives six independent RNG streams (entry, partnerships, knowledge, finance, exit, reputation) with SHA-256, obtained via `model.stream(name)`. The `knowledge` and `reputation` streams are reserved: their processes are deterministic in the current implementation.
- Same seed and parameters reproduce every stream and every step record.

### Period and scheduler

- `model.advance()` advances one period through the Mesa scheduler and returns the step record; `model.run_for(n)` advances n periods; `model.metrics()` returns the current record.
- `period` increments by exactly one per period and every step record includes it, per the metrics contract (ADR 0002).

### F1 limitations

- Only startups act: operating-cost accrual and failure exit.
- Anchor firms, universities, investors, workers, and the authority hold state but do not act.
- Environment values are stored but not yet used by any process.

## Phase F2 implemented mechanisms

All ten steps of the process order in `docs/architecture.md` are implemented. Defaults are calibration placeholders; `src/technology_park_abm/config.py` holds the authoritative values.

### Network

- `TypedNetwork` stores undirected weighted ties keyed by agent pair and semantic type ("partnership", "investment", "hiring").
- Tie strength is non-negative; partnership strength is `(compatibility + complementarity) / 2`.
- Exits remove all incident ties.

### Entry

- Each period draws `entry_potential_per_period` potential entrants from the "entry" stream.
- Entry probability is clipped to [0, 1]:
  `base + w_reputation * reputation + w_funding * funding_conditions + w_infrastructure * available_infrastructure + w_opportunity * mean_technology_quality - w_cost * cost_rate`,
  where `available_infrastructure = max(0, 1 - load / capacity)` and `cost_rate = burn_rate / initial_capital`.
- Infrastructure availability uses the previous period's load, since entry precedes the environment update.

### Partnerships

- Candidate partners are active startups plus anchor firms with participation "active".
- Each active startup makes `partnership_attempts_per_startup` random attempts per period.
- Formation probability is clipped to [0, 1]:
  `base + w_compatibility * compatibility + w_complementarity * complementarity + w_reputation * mean_reputation - w_cost * congestion`.
- Each existing partnership dissolves with probability `partnership_dissolution_probability` per period, before formation.

### Resource allocation and knowledge

- Each active startup gains `knowledge_rnd_gain * rnd_share` knowledge per period and `market_access_gain * (1 - rnd_share)` market access, capped at 1.
- `technology_quality` is `knowledge / (1 + knowledge)` for startups and anchors.
- Diffusion: for each partnership tie, the lower-knowledge endpoint gains `knowledge_spillover_rate * strength * difference`, applied synchronously after all pairs are evaluated.
- Knowledge depreciates by `knowledge_depreciation` per period.
- An innovation event counts each startup whose period knowledge gain (internal R&D plus diffusion) reaches `innovation_event_threshold`.

### Investment and hiring

- An investor with at least `investment_amount` available invests with probability `investment_probability` in a randomly chosen active startup whose quality is at least `investment_min_quality`; the amount transfers to the startup, sets its investor access to 1, and creates an "investment" tie.
- A startup hires with probability `hiring_probability` while below `max_team_size` and while unemployed workers exist; hiring adds `hiring_knowledge_gain * worker.skill` knowledge and creates a "hiring" tie.

### Finance and congestion

- Revenue is `revenue_per_access * technology_quality * access_to_clients`.
- Operating cost is `burn_rate + labor_cost_per_worker * (team_size - 1)`.
- Since v2.0.0 (V2-4), funding is survival-relevant: a startup with investor
  access (`access_to_investors >= 1`) pays `burn_rate * (1 - investor_burn_relief)`
  (default relief 0.25), so deactivating investors propagates to survival.
- Congestion: load is active startups plus anchor firms plus universities; each organization pays `congestion_cost_per_org * max(0, load - infrastructure_capacity)` per period.
- Capital is clamped at zero and failure is detected in the exit step.

### Exits

- "failure": capital reaches zero.
- "acquisition": requires at least one anchor firm, probability `acquisition_probability`, and quality at least `acquisition_min_quality`.
- "voluntary": probability `voluntary_exit_probability`.
- "migration": probability `migration_probability`.
- Exits remove all incident network ties and are counted per type in every step record.
- Since v2.6.0, an exit also lays off the exiting startup's workers: each worker with `employed_by` equal to the exited startup has it reset to `None`, returning to the unemployed pool. Hiring runs before exits in the period order, so a laid-off worker can be rehired from the next period on. Before v2.6.0 a worker kept a stale `employed_by` pointing at a dead startup and was never rehired, so `employment_total` under-recovered after exit waves.

### Reputation

- Target is cumulative survival, `active_startups / startup_count`.
- `reputation += reputation_update_rate * (target - reputation)`, clipped to [0, 1].

### Metrics added in F2

`entry_count`, `exit_count_by_type` (failure, acquisition, voluntary, migration), `active_tie_count`, `partnership_tie_count`, `knowledge_mean`, `innovation_count`, `employment_total`, `reputation`, `congestion`.

### F2 limitations

- Anchors do not initiate ties; universities hold state but do not act.
- No competition ties, spatial structure, policy effects, or investor capital replenishment.
- All parameters are stylized placeholders pending calibration (F5) and data work (F7).
- Agent reputation tracks observed technology quality (`reputation = knowledge / (1 + knowledge)`, refreshed each period), so the reputation term in partnership formation is a distinct, observable channel; the authority's collective reputation remains the entry signal.

## Phase F3 metrics, diagnostics, and reproducibility artifacts

### Complete metric suite

Every step record includes (metrics contract v1, ADR 0002):

- Population and work: `startup_count`, `active_startup_count`, `employment_total` (sum of team sizes of active startups, founders included).
- Ties: `active_tie_count`, `partnership_tie_count`, `productive_tie_count` (partnership strength at least `productive_tie_strength_threshold`, default 0.5).
- Network structure: `network_density` (realized share of possible partnership pairs among active startups) and `degree_centralization` (Freeman degree centralization among active startups).
- Knowledge and innovation: `knowledge_total`, `knowledge_mean`, `innovation_count`, plus (v2.0.0) `innovation_cumulative` (running total) and `quality_mean` (mean technology quality among active startups, the productivity-type output for H2).
- Capital and congestion: `capital_total`, `congestion`.
- Flows: `entry_count`, `exit_count_by_type` (failure, acquisition, voluntary, migration).
- Institution: `reputation`.

All metrics identify the simulation period.

### Increasing-returns diagnostic

`marginal_output(records, output_key, population_key="active_startup_count")` computes `G(N) = delta Y / delta N` between consecutive periods and skips periods with no population change. Rising values over a range of system size indicate increasing returns; falling values indicate saturation or congestion (E5).

### Snapshots and manifests

- `model.snapshot()` returns a JSON-serializable snapshot of the full state: period, configuration, environment, authority, network ties, and every agent (startups, anchors, universities, investors, workers).
- `build_manifest(config)` captures the ADR 0003 fields available before a run: schema version, creation timestamp, full configuration as parameters, seed list, package version, metric schema version, git commit and dirty state, and environment versions. The F4 runner adds run identifiers and output paths.

### F3 limitations

- Density and centralization consider partnership ties among active startups only; other tie types enter `active_tie_count`.
- The productive-tie threshold is a stylized placeholder pending calibration.
- Diagnostics operate on recorded series; there is no automated statistical detection of increasing returns yet.

## Phase F4 experiment runners, policy channels, and shocks

### Policy channels (E4)

Policy instruments are zero by default and enter existing mechanisms:

- `entry_subsidy` adds to entry attractiveness.
- `rnd_subsidy` multiplies internal R&D knowledge gain by `(1 + value)`.
- `shared_infrastructure` scales effective infrastructure capacity by `(1 + value)` for entry availability, congestion cost, and the congestion metric.
- `matchmaking` adds to partnership formation probability.
- `talent_program` multiplies hiring knowledge gain by `(1 + value)`.
- `investment_fund` is added to each investor's initially available capital.

### Shock scenarios (E6)

- `shock_period` and `shock_type` ("central_firm" or "funding") trigger one exogenous event at the start of the given period.
- "central_firm" collapses the top `shock_nodes` active startups by partnership degree (lowest id breaks ties; default 1, 3 in the E6 runner) by zeroing their capital, which produces failure exits in the same period.
- "funding" deactivates every investor, zeroes their available capital, and clears investor access for active startups.
- Shocks are deterministic and captured in every run manifest.

### Experiment runner

- `python -m technology_park_abm.experiments {E1..E6|all} --seeds ... --periods ... --output results`
- Every run writes `manifest.json` (multi-scenario mapping with full parameters), `metrics.csv` (one row per scenario × seed × period), and `summary.json` (final-period distributions per scenario: count, mean, min, max, median, q1, q3).
- Outputs carry a notice identifying them as simulation results, never empirical evidence.

### F4 limitations

- Scenarios are one-at-a-time, not a factorial cross of instruments.
- Summary statistics aggregate final-period values only; full trajectories live in `metrics.csv`.
- Policy magnitudes are stylized placeholders pending calibration.

## Phase F5 stylized calibration and pattern-oriented validation

### Calibrated defaults

Defaults in `config.py` were chosen to reproduce qualitative patterns, not empirical magnitudes: moderate survival with turnover, denser and more persistent partnership networks, capital heterogeneity, knowledge accumulation, and diffusion-driven innovation. The changes from the initial placeholders: `initial_capital` 100 -> 150; `congestion_cost_per_org` 2.0 -> 1.0; `entry_infrastructure_weight` 0.2 -> 0.5; `partnership_attempts_per_startup` 1 -> 2; `partnership_dissolution_probability` 0.05 -> 0.02; `knowledge_rnd_gain` 0.2 -> 0.3; `innovation_event_threshold` 0.15 -> 0.25.

### Pattern-oriented validation

`validation.py` provides `gini` (heterogeneity), `clustering_coefficient` (global transitivity), and `survival_rate`. Tests assert that a default 80-period run shows `0 < survival < 1`, positive capital dispersion, positive clustering, active partnership ties, population growth through entry, and knowledge accumulation. Reference values and limitations are in `docs/validation-report.md`.

### Internal validation

The pytest suite covers invariants, reproducibility of full histories and snapshots, direction-of-effect tests per mechanism, and data contracts (metric schema, snapshots, manifests).

### F5 limitations

- Calibration targets qualitative patterns only; there are no empirical magnitudes.
- Survival as "ever-created still active" is not a period hazard rate.
- Single-seed reference values; distributions belong to F6 sensitivity work.

## Phase F6 sensitivity, uncertainty, and regression guards

- `sensitivity.py` runs one-at-a-time variations around the calibrated defaults across multiple seeds and writes a manifest-style JSON report (`python -m technology_park_abm.sensitivity`).
- The report in `docs/sensitivity-report.md` identifies congestion cost and initial capital as the dominant parameters for population and capital, and knowledge spillover and partnership compatibility as the main drivers of knowledge and innovation.
- `tests/test_regression.py` pins a golden deterministic trajectory (default configuration, seed 7, ten periods) so unintended mechanism changes fail loudly.
- Uncertainty is reported as distributions across seeds (F4 summaries) and means in the sensitivity report; single-seed variation is material, so conclusions must be stated at the distribution level.

### F6 limitations

- One-at-a-time design cannot detect interactions; the non-monotonic congestion-innovation result indicates interactions worth a factorial design.
- Three seeds per configuration is a lower bound for uncertainty, not a final statistical standard.
- Golden regression tests must be updated deliberately when mechanisms change, with the change documented.

## Phase F7 public data pipeline

- `data/manifest.json` catalogs public sources with URL, license, status, access timestamp, and SHA-256 checksum; raw data stays in `data/raw/` and is never committed (ADR 0004).
- `python scripts/fetch_public_data.py` performs reproducible retrieval; the simulation itself never performs network access.
- Agent-level empirical calibration is currently infeasible with public data alone; the feasibility assessment and legal notes are in `docs/data-and-calibration.md`.

## Phase E1-E6 empirical enrichment (opt-in)

Defaults (`empirical_init="none"`, `sector_profiles="none"`, `connection_profile="baseline"`, `university_participation="passive"`) preserve the v1.3 behavior and goldens. Opt-in modes:

- `empirical_init`: `aggregates` samples worker (education, age, wage, skill), startup/anchor size classes, anchor employees, and university research quality from real published Brazilian aggregates (`empirical.py`, provenance in `AGGREGATE_SOURCES`; size-class and research-quality tables remain stylized); `microdata` resamples a canonical CSV (`education, age, wage, skill`) produced by the data pipeline. Deterministic via the derived `empirical` stream.
- `sector_profiles="brazil_tech"`: entry, exit and hiring probabilities are multiplied per sector (documented in `docs/playbooks.md`).
- `connection_profile="empirical"`: anchor-startup partnership bonus (+0.15), CNAE-inspired sector proximity bonus (weight 0.10), university-anchor co-patent channel proxy (+0.10), highest-quality investment target, highest-skill hiring; baseline behavior otherwise.
- Real anchor sample: with empirical initialization, anchor capital is drawn log-uniform from a real CNPJ sample (R$ 2.96-205.4 bn; `docs/empirical-calibration-report.md`); the data pipeline validates downloaded payloads and records checksums (`data/manifest.json`).
- `university_participation="active"`: universities join the partner pool, diffuse knowledge, and have quality/reputation refreshed like other agents.
- Metrics: `ties_formed_by_type` reports per-period partnership, investment, and hiring formations; the dashboard exposes a connections chip and table column.

## Calibration dashboard

`python -m technology_park_abm.dashboard` serves a loopback-only web UI (no new dependencies, ADR 0005) with parameter controls generated from `ModelConfig` and `Policy`, Apply/Reset, Step, Play/Pause controls, live metric charts, and a view of the typed network. The dashboard is a UI layer: it runs the same `TechnologyParkModel`, does not change model semantics or the metrics contract, and network positions are visual only.

## v2.2.0 verification, validation, and tooling additions

No model-behavior change; goldens untouched. The additions are analysis,
data-governance, and tooling layers:

- Experiment E7 (distributedness x resilience, H6): varies network distributedness via `partnership_reputation_weight` (`hub` 0.6 vs `distributed` 0.0) and measures recovery from a central-agent departure (`docs/experiments.md`).
- Trend detection: `mann_kendall_trend` (Mann-Kendall test) and `marginal_output_trend` (Sen's slope) in `metrics.py` for increasing-returns detection over recorded series.
- Recovery metrics in `summary.json` for every scenario with a shock (E6, E7): `recovery_<metric>` ratios (final vs last pre-shock period), `recovery_90pct` (share of seeds recovering at least 90% of pre-shock active startups), and `baseline_degree_centralization` (distributedness marker).
- `summary.json` distributions add `p10`/`p90` (inclusive quantiles, matching `numpy.percentile` defaults).
- Multi-seed parallelization: `--jobs N` runs independent (scenario, seed) runs in a process pool; results are identical for any `jobs` value.
- GSA estimators (`morris_effect_stats`, `sobol_indices_from_outputs`) cross-validated against SALib to machine precision; Sobol outputs are centered by the pooled mean and use population variance; Morris sigma uses the sample standard deviation (ddof=1).
- Data governance: data contracts schema 1.1 (`data_contracts.py`) require `legal_basis` and `personal_data` per source and mechanically forbid downloading personal-data sources (ADR 0012); five IBGE SIDRA aggregate sources ingested with real checksums.
- Toolchain (ADR 0013): committed `uv.lock`; `ty` and `pyrefly` alongside mypy strict; cosmic-ray as the distributable mutation runner; mutmut score 81.2% (target >= 70%).

## ODD-aligned model description

This section maps the model to the ODD protocol (Grimm et al. 2020). Mechanism formulas remain in the phase sections above.

### ODD summary

The technology park ABM simulates startups, one or more anchor firms, a university, investors, workers, and a park authority interacting over discrete periods. Startups enter based on the park's attractiveness, form and dissolve partnerships through a typed network, allocate effort between R&D and market access, diffuse knowledge through active ties, hire and receive investment, pay operating and congestion costs, and exit with distinguishable types; the authority's reputation feeds back into entry. Stochastic processes use independent seeded streams, scheduling is deterministic, and every mechanism and parameter is documented in the phase sections above.

### 1. Purpose and patterns

Purpose: understand when interactions in a technology park generate increasing returns and when congestion, concentration, or institutional weakness reverse them (`docs/research-plan.md`). Patterns used for validation: entry and turnover, partnership clustering, capital heterogeneity, knowledge accumulation, and diffusion-driven innovation (`docs/validation-report.md`).

### 2. Entities, state variables, and scales

Agents: startups, anchor firms, universities/ICTs, investors, workers, and the park authority (state tables in the phase F1 section). Environment: sectors, infrastructure, funding, labor market, and policy. Scales: one period is one planning cycle; there is no spatial dimension; the typed network is the only structure.

### 3. Process overview and scheduling

Each period executes, in fixed order: entry, environment update, network formation/dissolution, resource allocation, knowledge diffusion and depreciation, investment and hiring, finance and congestion, exits, reputation, and metrics. Scheduling is deterministic (no randomized activation order), which favors reproducibility and is a documented limitation for stochastic-order effects.

### 4. Design concepts

- **Basic principles**: increasing returns and congestion are emergent results to be tested, not assumed (H1-H6).
- **Emergence**: system-level growth and saturation arise from agent interactions; the G(N) diagnostic measures them.
- **Adaptation**: startups split effort between R&D and market access; allocation is a fixed rule, not learned.
- **Objectives**: startups pursue survival and growth indirectly; investors require a quality threshold; the authority responds to survival-driven reputation.
- **Learning and prediction**: not implemented; agents react to the current state only.
- **Sensing**: entrants sense reputation, funding, infrastructure, and opportunity; investors sense quality; startups sense partner knowledge; the authority senses survival.
- **Interaction**: partnership matching, knowledge diffusion, investment, and hiring. Competition ties are not implemented.
- **Stochasticity**: entry, partnership formation/dissolution, investment, hiring, and exits, each on its own seeded stream (see Randomness).
- **Collectives**: none; the authority is an agent, not a collective.
- **Observation**: the metrics contract, snapshots, and manifests; measurement is complete and error-free.

### 5. Initialization

Deterministic from configuration: fixed counts, round-robin sector assignment, given capital, zero knowledge, and derived RNG streams.

### 6. Input data

The default baseline does not require runtime external input data. Opt-in
empirical initialization uses the built-in public aggregates or the canonical
loader described above; the optional workbench permits synthetic/aggregate
modes and does not offer personal-microdata import. The pipeline and empirical
feasibility limits are documented in `docs/data-and-calibration.md`.

The optional investigation adapter records actual seeded metrics, events and
network frames without modifying these process rules. Its eleven interactive
starting options, including the new didactic size contrast, do not recalibrate
the baseline or register new hypotheses. See `docs/investigation-workbench.md`
and `docs/scenario-sota-review.md` for limits and interpretation.

### 7. Submodels

Entry probability, partnership formation/dissolution, allocation and diffusion, finance/investment/hiring, congestion, typed exits, and reputation, each with formulas and parameters in the phase F2/F4 sections. v2.0.0 additions: investor burn relief in finance, top-N central shocks, cumulative-innovation and mean-quality observation; real RAIS/PNAD worker marginals in empirical initialization (opt-in).

## TRACE traceability

| TRACE element | Artifact |
| --- | --- |
| Problem formulation | `docs/research-plan.md` |
| Model rationale | ODD design concepts above; ADRs 0001-0005 |
| Conceptual model | `docs/architecture.md`, `docs/model-specification.md` |
| Data evaluation | `docs/data-and-calibration.md` (F7 feasibility) |
| Implementation | `src/technology_park_abm/` |
| Verification | `tests/` (unit, invariants, fuzz, golden regression, end-to-end) |
| Calibration | `docs/validation-report.md` (stylized); v2.0.0 history-matching pilot in `docs/sensitivity-report.md` |
| Sensitivity | `docs/sensitivity-report.md` (OAT + interaction probe) |
| Validation | `docs/validation-report.md`, `docs/final-report.md` (v2.0.0 addendum) |
| Uncertainty | experiment summaries (F4) and sensitivity report (F6) |
| v2.0.0 journey | `docs/playbooks.md`, `ROADMAP.md`, journey gates in `tests/test_journey_gates.py` |
| v2.2.0 V&V and governance | E7, Mann-Kendall/Sen, recovery metrics, SALib cross-check (`docs/validation-report.md`, `docs/sensitivity-report.md`); data contracts (`docs/data-contracts.md`); toolchain (ADR 0013) |
| v2.3.0 UI (no model change) | "Atlas técnico" default theme + ecosystem-map SOTA rework (`DESIGN.md` §2.1, `docs/map-sota.md`); UI-layer only — model behavior, metrics contract, and goldens untouched; pinned by `tests/test_map_visualization.py`, `tests/test_ui_contracts.py`, `tests/test_a11y_browser.py` |
| v2.4.0 UI (no model change) | Nine-tour scenario suite (phenomenon/reference/hypothesis per tour; `docs/playbooks.md`, `docs/park-sota.md`) + leaderboard-style dashboard identity (`docs/benchmark-sota.md`); UI-layer only — model behavior, metrics contract, and goldens untouched; pinned by `tests/test_journey_gates.py`, `tests/test_ui_contracts.py`, `tests/test_gates.py`, `tests/test_a11y_browser.py` |
| v2.5.0 UI (no model change) | Dashboard page order rebuilt around the user journey (command → map → history → data → suite → help) with numbered section eyebrows, `--border-soft` internal borders, 16/10 park map, collapsible map legend, and footer (`DESIGN.md` §4/§5, `docs/design-system.md`); UI-layer only — model behavior, metrics contract, and goldens untouched; pinned by `tests/test_ui_contracts.py`, `tests/test_a11y_browser.py`, `tests/test_map_visualization.py` |
| v2.6.0 model fix + hardening | Layoff on exit: workers of an exiting startup return to the unemployed pool and can be rehired from the next period (semantics above; direction tests in `tests/test_processes.py`); mutation-test hardening with exact-value tests for `mann_kendall_trend`, `TypedNetwork`, `gini`, `clustering_coefficient`, `survival_rate`, `productive_tie_count`, `marginal_output_trend`, `degree_centralization` (`tests/test_metrics.py`, `tests/test_network.py`, `tests/test_validation.py`); per-release UX metrics recorded in `docs/ux-plan.md`. Golden trajectories at period 10 have zero exits and are unaffected; experiment reports (E1-E7) predate the fix and are regenerated on the v3 track |
