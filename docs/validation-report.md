# Validation report

Stylized calibration and pattern-oriented validation as of phase F5. All values are simulation output; none are empirical claims.

Scope update, 25/10/2026: the optional investigation workbench adds seeded
interactive experiments and literature-backed dossiers, without changing
this report's scientific evidence or calibrating new parameters. Its technical
verification, including A1–A5 presentation/export corrections
(513 tests, 93.64% coverage), is recorded separately in
`docs/verification-investigation-fixes-2026-10-25.md`. Source-backed initialization,
theoretical relevance and byte-identical reproduction are different from
independent process/output validation. Original figures below retain their
historical scope.

## Stylized calibration of defaults

Defaults in `src/technology_park_abm/config.py` were adjusted from the initial placeholders to reproduce qualitative patterns:

| Parameter | Placeholder | Calibrated | Rationale |
| --- | --- | --- | --- |
| initial_capital | 100.0 | 150.0 | Avoid premature mass failure while networks form |
| congestion_cost_per_org | 2.0 | 1.0 | Soften overshoot collapse above capacity |
| entry_infrastructure_weight | 0.2 | 0.5 | Strengthen congestion as an entry brake |
| partnership_attempts_per_startup | 1 | 2 | Allow denser partnership graphs |
| partnership_dissolution_probability | 0.05 | 0.02 | Make ties more persistent |
| knowledge_rnd_gain | 0.2 | 0.3 | Give internal R&D a visible trend |
| innovation_event_threshold | 0.15 | 0.25 | Make diffusion, not routine R&D, the main innovation source |

These are stylized choices for qualitative realism, not estimated parameters.

## Reference runs (default configuration, 80 periods)

| Seed | Started | Active | Survival | Clustering | Capital Gini | Partnership ties | Innovations (period 80) | Knowledge total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 88 | 16 | 0.182 | 0.454 | 0.301 | 38 | 6 | 34.85 |
| 1 | 88 | 18 | 0.205 | 0.339 | 0.287 | 39 | 9 | 35.42 |
| 2 | 90 | 18 | 0.200 | 0.332 | 0.407 | 41 | 7 | 38.36 |
| 3 | 95 | 17 | 0.179 | 0.379 | 0.348 | 41 | 6 | 38.45 |

Numbers reflect v1.2.0 (agent reputation tracks technology quality), which densifies partnership networks relative to v1.0.0.

Patterns reproduced qualitatively: entry and turnover (population grows while cumulative survival declines), partnership formation with nonzero clustering, concentration in capital (Gini), knowledge accumulation, and innovation events driven mainly by diffusion.

## Internal validation

The pytest suite covers:

- Invariants: non-negative capital, populations, counts, and exit categories; capital clamps at zero.
- Reproducibility: identical seeds reproduce full step histories, streams, and snapshots; interleaved runs share no state.
- Process behavior: direction-of-effect tests for entry, partnerships, diffusion, congestion, investment, hiring, exits, reputation, policy channels, and shocks.
- Contracts: metrics schema stability, snapshot JSON serializability, manifest fields.

## Validation hierarchy (aligned to the 2026 hierarchical ABM validation framework)

Reference: He et al., "Towards Standardizing Validation Practices in Agent-Based Modeling: A Hierarchical ABM Validation Framework", ACM Transactions on Modeling and Computer Simulation 36(1), January 2026, DOI 10.1145/3780102. The framework distinguishes calibration, verification, and validation as separate activities and organizes validation into a hierarchy in which credibility accumulates level by level. The project's evidence mapped onto that hierarchy:

| Level | Question | Evidence in this repo | Status |
| --- | --- | --- | --- |
| L1 Code verification | Is the code correct? | Unit, property (Hypothesis), and metamorphic suites; mutation testing (mutmut, target >= 70%); gates G1-G4 | Covered |
| L2 Conceptual validity | Is the model conceptually plausible? | ODD/TRACE documentation, `docs/model-specification.md`, stylized calibration of defaults | Covered (stylized) |
| L3 Process validity | Do the processes behave as specified? | Direction-of-effect tests per process (entry, partnerships, diffusion, investment, hiring, congestion, exits, reputation, policy, shocks) | Covered |
| L4 Pattern-oriented validation | Does the model reproduce stylized patterns? | `validation.py` (Gini, clustering, survival), reference runs above, E1-E7 scenario contrasts | Covered (stylized) |
| L5 Distributional validation | Do output distributions match reference distributions? | Multi-seed summaries with p10/p90 across E1-E7; seed-convergence study; Mann-Kendall trend detection (`metrics.py`) | Partial: targets are stylized bands, not empirical distributions |
| L6 Sensitivity and uncertainty quantification | Which parameters drive the outputs? | OAT screening, Morris/Sobol GSA cross-validated against SALib (`tests/test_gsa_crosscheck.py`), history-matching pilot | Covered (method) |
| L7 External (empirical) validation | Does the model match real-world observations? | Real public-data marginals (RAIS schooling/age, PNAD income, World Bank series, CNPJ anchor sample) feed agent attributes and connection priors; park-level historical validation is infeasible with public data | Open (documented in `docs/empirical-calibration-report.md`) |

Two 2026 additions close specific gaps in this hierarchy. E7 makes H6 testable by varying network distributedness (pre-shock `baseline_degree_centralization` in `summary.json`) and measuring recovery after a central-agent departure (`recovery_*` metrics, including the share of seeds recovering at least 90% of pre-shock active startups). The Mann-Kendall test with Sen's slope (`mann_kendall_trend`, `marginal_output_trend` in `metrics.py`) adds distribution-free trend detection for the increasing-returns question (H5's rising side), complementing the marginal-output analysis.

## Limitations

- Survival is "ever-created still active", not a period hazard rate; it declines mechanically over long horizons.
- Calibration targets patterns, not magnitudes; multiple parameter combinations may reproduce the same patterns.
- Clustering and Gini values are seed-sensitive; the table reports single seeds, not distributions.
- No empirical validation yet; see `docs/data-and-calibration.md` and the F7 feasibility assessment.
