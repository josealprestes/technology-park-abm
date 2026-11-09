# Test plan

SOTA-aligned test strategy for the technology park ABM, following the `research-software-testing` skill. It covers scope, risk-based priorities, levels and types, environments, data, entry/exit criteria, and a prioritized gap-closing backlog.

## 1. Objectives

- Protect scientific correctness: invariants, conservation identities, and contract stability.
- Protect reproducibility: identical seeds reproduce identical histories, snapshots, manifests, and experiment outputs.
- Catch mechanism and report regressions with fast, deterministic tests.
- Compensate for the oracle problem with property-based and metamorphic testing.
- Keep local checks reproducible and warning-free; record observed duration
  with each receipt instead of treating an old runtime as a budget.

## 2. Scope

In scope: `src/technology_park_abm/` (model, agents, environment, network, metrics, config, manifest, experiments, sensitivity, validation, dashboard, data pipeline), CLI entry points, and the CI workflow.

Browser JavaScript behavior is covered by Playwright/axe suites, including
the optional workbench. Out of scope: Mesa internals and external data sources
(no external network in tests; loopback HTTP allowed). Human comprehension,
screen-reader use and visual judgment remain manual evaluations.

## 3. Risk-based priorities

| Priority | Risk | Examples | Current coverage |
| --- | --- | --- | --- |
| P0 | Wrong science / silent corruption | invariants, exit accounting, determinism, metrics contract | strong (fuzz, golden, contract tests) |
| P0 | Non-reproducible published results | manifests, seeds, reproduction diff | strong (E1 byte-identical, tests) |
| P1 | Mechanism contradicts the specification | direction-of-effect tests per mechanism | strong |
| P1 | Experiment/report drift | runner reproducibility, manifest schema | medium (small-scale rows equality) |
| P2 | Input corruption via UI/CLI | dashboard coercion, CLI validation | medium (whole-number fix, HTTP 400s) |
| P3 | Performance regressions | 1000-period run, CI runtime | weak (manual probe) |

## 4. Levels and types (current inventory)

| Level/type | Location | Notes |
| --- | --- | --- |
| Unit | `tests/test_*.py` | agents, environment, network, metrics, config, manifest, validation |
| Integration | `test_processes`, `test_policy` | multi-mechanism, direction of effect |
| Property/fuzz | `test_fuzz` | 30 random configs; conservation identity |
| Golden/regression | `test_regression` | exact 10-period trajectory |
| Contract | `test_model`, `test_snapshot`, `test_manifest` | metric keys, JSON serializability, schemas |
| End-to-end | `test_end_to_end` | 300 periods; cross-process smoke determinism |
| CLI/HTTP | `test_experiments`, `test_sensitivity`, `test_dashboard` | argparse mains; loopback server |
| Statistical | planned (T2) | rates within confidence intervals |
| Metamorphic (model-change) | planned (T3) | oracle-less validation relations |
| Mutation | planned (T5) | suite-strength measurement |

Categories are enforced with pytest markers and runnable in isolation: `pytest -m unit`, `pytest -m regression`, `pytest -m smoke`, `pytest -m e2e`, `pytest -m gate`, `pytest -m a11y`. Tests without an explicit category default to `unit` via `tests/conftest.py`; end-to-end tests inside mixed files carry a function-level `e2e` marker; deterministic skill-derived gates carry both `unit` and `gate` markers so the gate subset runs fast via `pytest -m gate`. `tests/test_smoke.py` exercises every entry point in a real subprocess (module demo, experiment CLI, sensitivity CLI, dashboard server).

## 5. Test design techniques

- Equivalence partitioning and boundary values for configurations (zero capacity, zero capital, empty populations, huge values, shocks without targets); formalize the audit probes in T6.
- Invariant properties: non-negativity, conservation (`created - active == cumulative exits`), idempotence of derived state, config/effective-params round-trip.
- Metamorphic relations (NIST categories): parameter-change MRs (higher compatibility weakly increases ties; higher capacity weakly reduces congestion cost) and model-change MRs (adding a passive anchor does not reduce startup ties).
- Statistical oracles for stochastic mechanisms: empirical entry rate within a binomial interval over many seeds; tie formation at probability 1 forms exactly the attempted ties.
- Golden/approval tests for numeric trajectories, updated deliberately with a documented commit note.

## 6. Environments and CI

- Local: Windows, Python 3.12 virtual environment.
- `scripts/run_checks.py` replaces the removed GitHub Actions workflow:
  ruff check/format, mypy/ty/pyrefly, pytest with warnings as errors and
  coverage, package/experiment/sensitivity smokes and data policy. The old
  Python 3.12/3.13/3.14 CI matrix is not claimed by a local Python 3.12 run.
- Network policy: no external calls in tests; loopback HTTP is allowed;
  public data downloads belong to the pipeline and are not automatic tests.

## 7. Test data management

- Seeds are explicit; golden values pinned; `results/` and `data/` are gitignored.
- Fixtures live in tests; no shared mutable state between tests (guarded by the interleaving test).
- Flaky policy: any intermittent test is quarantined within one day, root-caused, and fixed or deleted; no silent retries in CI.

## 8. Entry and exit criteria

The development loop follows the `agentic-swe-workflow` skill: spec first, smallest verifiable increment, verification gates, anti-reward-hacking rules, and documentation in the same change.

- Entry: feature branch with documentation updates; ruff and mypy clean.
- Exit: full suite green on all CI Pythons; new behavior has invariant plus direction/MR tests; goldens updated deliberately; reproduction diff unchanged or explained; manifests updated.

## 9. Gap-closing backlog

| ID | Item | Priority | Effort | Maps to | Status |
| --- | --- | --- | --- | --- | --- |
| T1 | Property-based tests (Hypothesis) for TypedNetwork, config coercion, and model invariants (stateful machine) | P1 | M | R1 | done (`tests/test_properties.py`) |
| T2 | Statistical tests for stochastic mechanisms (entry/tie/exit rates over seeds with intervals) | P1 | M | R1/R2 | done (`tests/test_statistics.py`) |
| T3 | Formal metamorphic suite (parameter-change and model-change MRs) | P1 | M | R2 | done (`tests/test_metamorphic.py`) |
| T4 | Coverage reporting (pytest-cov) with a threshold (>= 90% line on `src`) | P1 | S | R5 | done (threshold in `pyproject.toml`) |
| T5 | Mutation testing (mutmut) on core modules; target score >= 70% | P2 | M | R5 | adopted as a local step (`scripts/run_checks.py --full`); mutmut has no native Windows support (upstream #397), so it is not in the default local battery; **score measured 2026-10-23: 96.4%** (374 killed / 388 total, 14 survived, 0 without tests; scope `network.py` + `metrics.py` + `validation.py`, 19 in-process test files; ADR 0013). cosmic-ray (`cosmic-ray.toml`) is the config-driven distributed runner for CI. v2.6.0 follow-up closed: exact-value tests for `mann_kendall_trend` (no-ties, partial ties, weak/balanced, n<2, strict alpha boundary), anchored `pytest.raises(match=...)` on error messages, and type/threshold/outsiders tests for `productive_tie_count`, `degree_centralization`, `clustering_coefficient`, `survival_rate`, `marginal_output_trend`, `TypedNetwork`. The 14 remaining survivors are equivalent mutants, each documented: `zip(strict=False)`→`strict=None` and dropped `strict=False` (both falsy-equivalent, `marginal_output`); `// 2`→`/ 2` on always-even `degree*(degree-1)` (value-equal, `clustering_coefficient`); `range(count-1)`→`range(count+1)` (extra iterations empty, `mann_kendall_trend` x2); `variance <= 0.0`→`< 0.0` and `<= 1.0` (variance 0 implies statistic 0; minimum positive variance is 1.0 with z=0 either way); `statistic > 0`→`> 1` and `p < alpha and statistic > 0`→`>= 0`/`> 1` plus the `statistic < 0` counterparts (statistic 0 or ±1 implies z = 0, p = 1, never significant); `degrees` initialized to 1 (shift-invariant centralization, `degree_centralization`); `_pair` `first < second`→`<=` (equal ids yield the same tuple) |
| T6 | Formal boundary/edge test module (zero capacity/capital/population, huge values, shocks without targets) | P2 | S | audit A4 | done (`tests/test_boundaries.py`) |
| T7 | DashboardSession concurrency test (parallel step/state under the lock) | P2 | S | R5 | done (`test_dashboard.py`) |
| T8 | Schema contract tests for `metrics.csv`, `summary.json`, and manifest JSON | P2 | S | R1 | done (`tests/test_contracts.py`) |
| T9 | Performance smoke with a generous budget (1000 periods under a threshold) | P3 | S | R5 | done (`tests/test_performance.py`, 500 periods under 60 s) |
| T10 | Experiment reproduction check in CI (deterministic rows hash for a small suite) | P2 | S | R2 | done (`tests/test_reproduction.py`, byte-level) |
| T11 | Reputation update rule tests (direction of effect plus deliberate golden update) | P1 | S | R3 | done (with R3) |
| T12 | UI/accessibility contract suite (labels, accessible names, data-table toggle, Okabe-Ito palette, computed contrast) | P1 | M | UX-A/UX-B (`docs/ux-plan.md`) | done (`tests/test_ui_contracts.py`, extended by `tests/test_map_visualization.py` for canvas-drawn labels and pointer behavior) |
| T28 | Map readability pass (region counts, type-colored outlines, non-mutating hover focus, dynamic canvas accessible name, declared node-size transform) | P1 | M | user report; web-dashboard-svg-canvas reference of `scientific-visualization` | done (`tests/test_map_visualization.py` measures painted text and pointer behavior; `tests/test_a11y_browser.py` updated for highlight-not-hide drill) |
| T29 | Ecosystem-map SOTA pass (DPR-crisp canvas, strength-ordered overplotting, rest/focus alpha, curved parallel pairs, degree-priority + collision-skipped labels, region tint, taller fluid canvas) | P1 | M | user report "mapa ruim"; `docs/map-sota.md`, skill `.opencode/skills/map-viz` | done (P1 items implemented; new tests: DPR backing store, node-label non-overlap, `test_map_sota_rendering_contracts`; hover test scrolls map into view; goldens/model untouched) |
| T30 | General UX/dataviz SOTA gate pass (G13 single-file loopback, G14 interaction contracts, G15 dataviz contracts; nice ticks ≤5/band; 24px targets; ESC/focus-return) | P1 | M | user request; `docs/ux-sota.md`, `docs/dataviz-sota.md`, skill `.opencode/skills/design-gates` | done (P1 machine-checkable items implemented; CSV-vs-table full identity recorded as explicit deviation; multi-seed uncertainty stays in experiments output by design; manual items — SUS, tour completion, prose — stay in `docs/ux-plan.md`) |
| T31 | Applied SOTA improvements (live figure takeaways, run busy state, error recovery copy, KPI→glossary linkage, seed note in captions) | P1 | M | user request "aprimore com base no que aprendeu"; G14/G15 gates | done (behavior pinned by static + browser gates; model/goldens untouched) |
| T32 | Map label legibility (12px labels, 11px narrow canvas, `--panel-2` halo, side chosen by available space, clamped inside canvas, region titles painted last) | P1 | S | user report "mapa ruim"; `docs/map-sota.md` | done (`tests/test_map_visualization.py` + `tests/test_ui_contracts.py`; goldens/model untouched) |
| T33 | Atlas técnico default theme + ecosystem-map SOTA rework (flow arrows investor→startup / worker→firm, edge-strength labels on focus, employed-worker ink dot, ink edge casing on light plates, cartographic marginalia with period/seed/congestion; four-theme cycle atlas→dark→light→contrast) | P1 | M | user chose V1 "Atlas técnico" identity; user report "mapa ruim"; `docs/map-sota.md`, `DESIGN.md` §2.1 | done (new tests: ink casing, marginalia, strength labels in `tests/test_map_visualization.py`; atlas contrast/structure in `tests/test_ui_contracts.py`; theme-cycle updated in `tests/test_a11y_browser.py`; goldens/model untouched) |
| T34 | Scenario suite + leaderboard identity (9 tours with phenomenon/reference/hypothesis fields; dense clickable suite table with caption + scoped headers; snapshot line; guide meta-chips; honesty microcopy; nav link; changelog 2.4.0) | P1 | M | user request "revisão dos cenários" grounded in innovation-economics literature; `docs/park-sota.md`, `docs/benchmark-sota.md` | done (tests: literature anchors + suite-table contracts in `tests/test_journey_gates.py`; UI contracts in `tests/test_ui_contracts.py`; table contract in `tests/test_gates.py`; browser row-click + meta-chips in `tests/test_a11y_browser.py`; goldens/model untouched) |
| T35 | Dashboard page order + visual breathing room (journey order comando → mapa → histórico → dados → suíte → ajuda; § 01–§ 06 eyebrows; --border-soft; spacing scale; map 16/10; collapsible legend; footer; Dados nav opens table) | P1 | M | user report "caótico" + UX/journey SOTA (`docs/ux-sota.md`, `docs/journey-sota.md`) | done (tests: section-order + border-soft contracts in `tests/test_ui_contracts.py`; a11y 30/30; screenshots 4 temas; goldens/model untouched) |
| T36 | Layoff on employer exit + mutation hardening + per-release UX metrics (model fix: `_exit_startup` resets `employed_by` to the unemployed pool; exact-value tests for `mann_kendall_trend`/`TypedNetwork`/`gini`/`clustering_coefficient`/`survival_rate`/`productive_tie_count`/`marginal_output_trend`/`degree_centralization`; anchored error-message matches; time-to-first-insight + tour completion + SUS single-rater recorded) | P1 | M | handoff open items (layoff bug, mutation follow-up, UX manual metrics); V3-0; `docs/ux-plan.md` | done (direction tests in `tests/test_processes.py`; exact-value tests in `tests/test_metrics.py`/`test_network.py`/`test_validation.py`; mutation score 81.2% → 96.4% (374/388, 14 equivalent survivors documented in T5); goldens at period 10 unaffected — zero exits; experiment reports predate the fix, regenerated on the v3 track) |
| T20 | Automated browser a11y (headless Chromium: zero console errors, zero axe violations, keyboard reachability, welcome→tour→nudge journey, checklist persistence) | P1 | M | UX-F, ADR 0006 | done (`tests/test_a11y_browser.py`, `pytest -m a11y`; Chromium via `playwright install chromium`; CI installs it) |
| T21 | UI/UX upgrade L1-L3 (control hierarchy, collapsed help/changelog, nudge severity, mobile wrap; KPI deltas, edge toggles, empty-region skip, collapsible details; inline-SVG charts with keyboard inspection per ADR 0007) | P1 | L | benchmarks (Mesa SolaraViz, ArcGIS, Tableau, shadcn) | done (`tests/test_journey_gates.py`, `test_ui_contracts.py`, `test_a11y_browser.py`; zero axe violations kept) |
| T22 | Concise scannable content (NN/g + GovBR/VA chunking: shortened help, glossary/definition lists, tour progress bar, curated node-facts card) | P1 | S | content benchmarks | done (`tests/test_ui_contracts.py`; screenshots verified) |
| T23 | Layout redesign (sticky toolbar + in-page nav, KPI cards with sparklines + deltas, light/dark theme with contrast gates both themes, visible map title, parseInt period fixes, Conexões chip retired) | P1 | L | shadcn anatomy, ArcGIS nav, dashboardcn KPI | done (static + browser tests incl. light-mode axe; screenshots dark/light verified) |
| T24 | Executive shell for senior professors (grouped toolbar + "Mais ferramentas" menu, Calibrar drawer closed by default, clickable KPI delve, high-contrast theme + prefers-contrast, larger type/targets) | P1 | M | Tabler/AdminLTE/Pico patterns (tokens ported, zero-dep kept) | done (static + browser tests incl. contrast-mode axe) |
| T25 | Full-cast context (empty regions as faint "(vazio)" placeholders, "Em cena" cast line, Tour dados reais with all six actor types, applyParamsWith fix for dropped advanced preset params) | P1 | M | user report of missing actors | done (`tests/test_journey_gates.py`, `test_a11y_browser.py` regression; screenshots verified) |
| T26 | Pico.css theme vendored (MIT, offline, app styles win ties; :root[data-theme] bridge for dark/light/contrast; toolbar/pagenav specificity fixes) | P1 | M | Tabler/AdminLTE/Pico research, ADR 0008 | done (`tests/test_ui_contracts.py`; axe zero in 3 themes; screenshots verified) |
| T27 | Executive shell (sidebar nav + actions, Ctrl+K command palette, KPI drill-down with edge isolation, Tabler-style page header) | P1 | L | Tabler/Grafana visual benchmarks, ADR 0009 | done (static + browser palette/drill tests; screenshots verified) |
| T13 | Deterministic skill-gate suite (static randomness/network scans, ODD/TRACE docs-sync, traceability sync, manifest STRESS fields, gate-runner pin) | P1 | S | adversarial P2/P5, workflow gates | done (`tests/test_gates.py`, `scripts/check_gates.py`, `pytest -m gate`) |
| T14 | Journey/preset contract suite (tour guidance, preset grouping and end-to-end determinism, scenario round-trip, deterministic CSV export, empty states) | P1 | S | smooth-journey skill, UX-D | done (`tests/test_journey_gates.py`, `pytest -m gate`) |
| T15 | V2-1 journey tests (interactive tour checklist persistence, nudge predicates as pure state functions, empty-state single action) | P1 | M | V2-1 (`docs/v2-plan.md`) | done (extend `tests/test_journey_gates.py`; goldens untouched) |
| T16 | V2-2 storytelling tests (annotation/diff static contracts) plus manual protocol (time-to-first-insight, tour completion, SUS) | P2 | M | V2-2 (`docs/v2-plan.md`) | done (`tests/test_journey_gates.py`; manual measurements pending real sessions) |
| T17 | V2-3 heterogeneity tests (marginals within tolerance and joint correlations preserved, snapshot checksum in manifests) | P1 | M | V2-3 (`docs/v2-plan.md`) | done (`tests/test_empirical.py`; code version + commit identify the snapshot; goldens unaffected) |
| T18 | V2-4 mechanism tests (productivity outputs for H2, survival-relevant funding and stronger shocks for H6; single deliberate golden update) | P1 | L | V2-4 (`docs/v2-plan.md`) | done (`tests/test_processes.py`, `test_model.py`; goldens in `tests/test_regression.py`) |
| T19 | V2-5 calibration-pilot tests (determinism, shapes, budget guards for history matching) | P2 | M | V2-5 (`docs/v2-plan.md`) | done (`tests/test_sensitivity.py`, `--history-matching` CLI) |

R4 (empirical validation) has no automated tests while no data is available; it is tracked as a conditional phase in `docs/remediation-plan.md`.

Dependencies adopted with justification per `AGENTS.md`: `hypothesis` for T1 (property-based testing detects far more mutations per test than unit tests, OOPSLA 2025), `pytest-cov` for T4 (coverage gate), `mutmut` for T5 (local mutation step; no native Windows support), `SALib` (dev-only, 2026-10-22) as the reference implementation for cross-validating the Morris/Sobol estimator cores in `tests/test_gsa_crosscheck.py`, and the 2026 toolchain (ADR 0013, dev-only, never runtime): `ty` and `pyrefly` as additional static type checkers alongside mypy in `scripts/run_checks.py`, and `cosmic-ray` as the config-driven distributed mutation runner (`cosmic-ray.toml`). The full transitive closure is pinned in the committed `uv.lock`.

## 10. Traceability

| Requirement | Tests |
| --- | --- |
| Metrics contract v1 (ADR 0002) | `test_model`, `test_snapshot`, `test_manifest` |
| Reproducibility | `test_config`, `test_end_to_end`, `test_regression`, reproduction diff |
| Invariants | `test_fuzz`, `test_processes`, `test_model` |
| Mechanisms E1-E6 | `test_processes`, `test_policy`, `test_experiments` |
| Investigation workbench: paired raw-model evidence, reproduction, observe/compare, custom execution, draft/result separation, validation/cancellation, supported research contrasts, source export, loopback-only self-containment (G13), synthesis + Mann-Kendall verdicts, keyboard, axe and mobile reflow | `test_investigation_prototype` |
| Workbench A1–A5: effective metric definition and incompatible-threshold delta guard; independent CSV reproduction including p0 and each row's seed; network-abort retry; self-contained figure scope and 16 px essential mobile reading | `test_investigation_prototype` (real jobs, browser, CSV round-trip and model replay; projection remains manual) |
| Workbench verdicts (Wave 1): synthesis + per-series Mann-Kendall on the mean across seeds, short-series honesty, congestion alert, JSON export schema 4 (server-computed for live jobs, browser-computed for cached examples) | `test_investigation_prototype` (verdict determinism + honesty tests; server probes) |
| Data policy (ADR 0004) | `test_data_pipeline`, `test_gates`, local runner data-policy step |
| ODD/TRACE documentation | `test_gates` (section presence; prose quality stays manual) |
| Manifest STRESS fields | `test_gates` |
| Skill-gate runner | `test_gates`, `scripts/check_gates.py` |
| Loopback self-contained workbench + no chart libs (G13) | `test_gates` (sources), `test_investigation_prototype` (behavior) |

## References

- Martin Fowler, The Practical Test Pyramid.
- ICSE 2024, Property-Based Testing in Practice; OOPSLA 2025, Empirical Evaluation of PBT in Python.
- Chen et al., metamorphic testing; NIST, MT on the continuum of simulation V&V.
- Kanewala et al., Testing Scientific Software: A Systematic Literature Review.
- AAMAS 2020, Specification testing of ABS using PBT; ACM TOMACS 2026, hierarchical ABM validation framework.
- Papadakis et al., mutation testing advances; NIST numerical reproducibility; STRESS reporting guidelines.
