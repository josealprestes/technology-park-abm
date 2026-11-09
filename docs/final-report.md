# Final report (v2.0.0)

Scope note, 24/10/2026: this is a historical scientific report, not the current
software handoff. The post-v2.13.0 optional workbench and its scenario review
are documented in `docs/investigation-workbench.md` and
`docs/scenario-sota-review.md`. Its technical checks do not replace the
experiments or revise the verdicts below. Current software verification:
`docs/verification-investigation-2026-10-24.md`.

Consolidated results for version 1.2.0 of the technology park ABM, with a v2.0.0 addendum at the end. Section 1 numbers are simulation output from the experiment runners (`docs/experiments.md`) executed at commit `4962b34` with seeds 1-5 and 60 periods (E2 also at 120); none are empirical claims. Behavior changed in v1.2.0 (agent reputation now tracks technology quality) and in the E4/E6 scenario design (binding funding); goldens were updated deliberately.

## What was built

- Mesa-based agent model with startups, anchor firms, universities, investors, workers, and a park authority (`docs/model-specification.md`).
- Ten-step process order: entry, environment, network formation/dissolution, resource allocation, knowledge diffusion, investment and hiring, finance and congestion, typed exits, reputation, metrics.
- Metrics contract v1 with the full suite, increasing-returns diagnostic G(N), JSON snapshots, and run manifests (ADRs 0002/0003).
- Experiment runners E1-E6 with multi-seed distributions and persisted manifests (`src/technology_park_abm/experiments.py`).
- Stylized calibration and pattern-oriented validation (`docs/validation-report.md`); OAT and interaction sensitivity (`docs/sensitivity-report.md`).
- Local calibration dashboard (v1.1.0, ADR 0005); ODD/TRACE-aligned documentation; explicit test categories (unit/regression/smoke/e2e) and a SOTA-aligned test plan (`docs/test-plan.md`).
- Public data catalog and retrieval pipeline with checksums; empirical feasibility assessment (`docs/data-and-calibration.md`).

## Hypothesis verdicts

Means across seeds 1-5, final period (60), unless noted; full distributions in the run summaries under `results/v120/`.

### H1: A critical mass of complementary agents increases productive partnership formation

**Supported within range, non-monotonic beyond capacity (E1).**

| Initial startups | Active (final) | Partnership ties | Knowledge total |
| --- | --- | --- | --- |
| 2 | 1.8 | 0.8 | 5.1 |
| 8 | 7.2 | 20.4 | 19.8 |
| 16 | 1.8 | 1.2 | 4.9 |

Partnership formation rises steeply from 2 to 8 agents; a population above infrastructure capacity collapses (H5 interaction).

### H2: Diversity produces stronger innovation when sectors are technologically complementary

**Inconclusive (E2).** Compatibility strongly changes tie formation, but not knowledge outcomes, and differences vanish at longer horizons.

| Mix (60 periods) | Partnership ties | Knowledge total | Knowledge mean |
| --- | --- | --- | --- |
| Concentrated | 20.8 | 19.8 | 2.75 |
| Complementary | 20.4 | 19.8 | 2.75 |
| Unrelated | 11.2 | 19.7 | 2.73 |

At 120 periods all mixes converge to the same steady state (about 3.8 active startups, 10.8 knowledge, 5-6 ties): diversity effects are transient, and diffusion redistributes rather than creates knowledge. Testing H2 requires productivity-type outputs and controlled horizons.

### H3: Anchor firms create positive spillovers only when they actively participate

**Partially supported, with congestion caveats (E3).**

| Anchor setup | Active (final) | Partnership ties | Knowledge total | Knowledge mean |
| --- | --- | --- | --- | --- |
| Absent | 7.2 | 20.4 | 19.8 | 2.75 |
| Passive | 4.6 | 7.8 | 12.6 | 2.75 |
| Active | 4.6 | 11.0 | 13.0 | 2.83 |
| Multiple active | 3.6 | 13.4 | 10.4 | 2.87 |

An active anchor raises ties (+41%) and per-firm knowledge (+3%) relative to a passive one at equal population, consistent with the mechanism. Anchors also add to infrastructure load: relative to no anchor, population and total knowledge fall, and multiple anchors crowd the park further.

### H4: Connection infrastructure and shared facilities outperform indiscriminate entry subsidies on innovation outcomes

**Supported (E4).** The investment fund now binds (investor capital 10 vs 100), unlike v1.0.0.

| Instrument | Active (final) | Ties | Knowledge total | Knowledge mean | Innovations |
| --- | --- | --- | --- | --- | --- |
| Baseline | 15.0 | 30.6 | 28.2 | 1.88 | 5.8 |
| Entry subsidy | 18.6 | 22.4 | 20.2 | 1.09 | 6.0 |
| R&D subsidy | 14.4 | 33.6 | 42.9 | 2.99 | 9.2 |
| Shared infrastructure | 17.2 | 36.6 | 36.1 | 2.10 | 5.2 |
| Matchmaking | 14.8 | 57.0 | 35.1 | 2.38 | 5.0 |
| Talent program | 15.0 | 30.4 | 28.2 | 1.88 | 5.4 |
| Investment fund | 14.4 | 28.0 | 26.7 | 1.86 | 5.4 |

R&D subsidy, shared infrastructure, and matchmaking all outperform the entry subsidy on knowledge (35-43 vs 20) and the baseline (28). The entry subsidy grows population (+24%) but dilutes per-firm knowledge (1.09 vs 1.88). The investment fund binds but has a modest, slightly negative knowledge effect in this calibration, so the funding channel is weak for knowledge.

### H5: Increasing returns eventually face a congestion threshold

**Supported (E5).**

| Population (capacity 8) | Active (final) | Capital total | Knowledge total | Ties |
| --- | --- | --- | --- | --- |
| 4 | 3.8 | 446.8 | 10.7 | 5.2 |
| 8 | 7.2 | 517.4 | 19.8 | 20.4 |
| 16 | 1.8 | 101.4 | 4.9 | 1.2 |

Doubling the population from capacity collapses survival, capital, knowledge, and ties: the marginal contribution turns negative beyond capacity.

### H6: More distributed networks are more resilient to the departure of a central agent

**Inconclusive (E6), with an explanation.**

| Scenario | Active (final) | Knowledge total | Ties |
| --- | --- | --- | --- |
| Baseline | 15.0 | 28.2 | 30.6 |
| Central firm collapse | 15.0 | 27.9 | 28.8 |
| Funding collapse | 15.0 | 28.2 | 30.6 |

The central-firm shock is almost fully absorbed (entry and rewiring compensate). The funding shock has no measurable effect because investment is not essential to survival at these defaults: deactivating investors does not change active population or knowledge. Resilience cannot be distinguished until funding becomes survival-relevant (for example, capital-constrained startups dependent on investment) and shocks are stronger.

## Overall interpretation (simulation only)

- Park size is governed by the interaction of entry attractiveness and congestion; capacity is the pivotal policy variable in the model.
- Knowledge outcomes respond more to diffusion channels (R&D subsidy, matchmaking, shared infrastructure) than to population growth; entry subsidies dilute per-firm knowledge.
- Diversity effects on knowledge are transient and disappear by 120 periods in this calibration; total knowledge is a poor discriminator because diffusion redistributes it.
- The funding channel binds in behavior (investor capital) but not in outcomes (survival does not depend on investment), which explains the H6 null result.
- Agent reputation now tracks observed technology quality, making the reputation channel in partnership formation active.

## Limitations

- Stylized calibration only; no empirical magnitudes (see `docs/data-and-calibration.md`).
- Five seeds per configuration; sensitivity analyses (Morris/Sobol) are the next step (R1 in `docs/remediation-plan.md`).
- E2 differences vanish at 120 periods; knowledge totals are near-conserved under diffusion.
- Funding shocks do not propagate to survival at current defaults.
- No spatial structure, competition ties, university behavior, or investor replenishment.
- Empirical agent-level calibration and historical validation are infeasible with public data alone.

## Reproduction guide

From a clean checkout at v1.2.0:

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows; use source .venv/bin/activate elsewhere
pip install -e .[dev]
pytest                             # full suite, including regression guards
python -m technology_park_abm      # deterministic smoke run
python -m technology_park_abm.experiments all --seeds 1 2 3 4 5 --periods 60 --output results/v120
python -m technology_park_abm.experiments E2 --seeds 1 2 3 4 5 --periods 120 --output results/v120
python -m technology_park_abm.sensitivity --seeds 1 2 3 --periods 60
```

Reference runs for this report: `results/v120/E1-20261007T124138Z-4962b34` through `E6-20261007T124140Z-4962b34`, plus the 120-period E2 run `E2-20261007T124142Z-4962b34`. Same commit, seeds, and periods reproduce identical metrics.

## Next steps

1. R1: Morris screening and Sobol indices with a seed-convergence study (`docs/remediation-plan.md`).
2. Make funding survival-relevant (investment-dependent costs or capital constraints) and strengthen shocks to retest H6.
3. Productivity-type outputs for H2; factorial designs over congestion x diffusion.
4. Restricted microdata or park administrative records (with legal basis) for empirical calibration.

## Addendum v2.0.0 — H2/H6 retest (V2-4)

All numbers below are simulation output from `results/v200/` (commit
`89870d0`, seeds 1-5, 60 periods unless noted); none are empirical claims.
Sections above (v1.2.0) are preserved unchanged.

### What changed in the model

- `investor_burn_relief = 0.25` (new default): startups with investor access
  pay 75% of `burn_rate`, making funding survival-relevant at defaults.
- `shock_nodes` (new config, default 1): the central shock collapses the
  top-N startups by partnership degree; the E6 runner uses 3.
- New additive metrics: `innovation_cumulative` (running total) and
  `quality_mean` (mean technology quality among active startups) — the
  productivity-type outputs H2 needed.
- E6 `resilience_base` investor capital corrected 20 → 100: with
  `investment_amount = 50`, a capital of 20 could never invest, so the
  v1.2.0 funding null was partly a design artifact. The first E6 rerun
  (`E6-20261013T180906Z-89870d0`) is superseded by
  (`E6-20261013T181013Z-89870d0`).
- Golden trajectories updated deliberately (existing keys byte-identical;
  two additive keys appended); see `tests/test_regression.py`.

### Revised verdicts

Means across seeds 1-5, final period (60), unless noted.

**H1: supported (unchanged shape).** 2 → 1.8 active / 259.2 capital; 8 →
7.2 / 551.3 / 20.8 ties; 16 → 1.8 / 124.9 / 1.2 ties. Capital levels
shifted vs v1.2.0 because the base scenarios hold investors (relief now
applies); the non-monotonic shape is identical.

**H2: not supported in this calibration (upgraded from inconclusive).**
Ties still differ (concentrated 21.0, complementary 20.8, unrelated 10.8)
but no productivity output responds at either horizon:

| Mix | Quality mean (60) | Quality mean (120) | Cumulative innovations (60/120) |
| --- | --- | --- | --- |
| Concentrated | 0.73 | 0.74 | 0.0 / 0.0 |
| Complementary | 0.73 | 0.74 | 0.0 / 0.0 |
| Unrelated | 0.73 | 0.74 | 0.0 / 0.0 |

Without entrants, diffusion redistributes knowledge but creates no
innovation events under the current threshold, so diversity cannot move
productivity outputs here. A documented null with an explanation, not a gap.

**H3: supported, strengthened.** Active vs passive anchor at equal
population (4.6): ties 11.0 vs 7.8 (+41%), knowledge mean 2.83 vs 2.75,
and now cumulative innovations 37.8 vs 0.0 (multiple active: 52.8) — the
spillover is visible in innovation output, not just ties. Crowding caveat
unchanged (population and total knowledge below the no-anchor case).

**H4: supported, amplified.** R&D subsidy cumulative 534.6 vs baseline
272.6; entry subsidy dilutes per-firm quality (0.49 vs 0.61) while growing
population (+24%). The investment fund stays weak (cumulative 268.8 vs
272.6; capital 970.8 vs 974.8): the funding channel binds in behavior but
barely in knowledge outcomes.

**H5: supported (unchanged shape).** 16 startups on capacity 8 collapse to
1.8 active, capital 124.9, ties 1.2.

**H6: inconclusive by design, with quantified absorption.** E6 varies shock
presence, not network distributedness, so the hypothesis as stated remains
untestable. Shocks are now measurable rather than null:

| Scenario | Active | Capital | Knowledge | Ties | Cumulative |
| --- | --- | --- | --- | --- | --- |
| Baseline | 14.4 | 970.8 | 27.06 | 28.6 | 268.8 |
| Central collapse (3 nodes) | 14.6 | 976.7 | 27.09 | 32.4 | 267.0 |
| Funding collapse | 14.2 | 967.4 | 25.93 | 26.2 | 265.4 |

Funding collapse costs ~4% of knowledge with binding funding; the 3-node
central collapse is fully absorbed and slightly over-compensated via
congestion relief and rewiring (ties rise 28.6 → 32.4).

### v2.0.0 reproduction

```bash
python -m technology_park_abm.experiments all --seeds 1 2 3 4 5 --periods 60 --output results/v200
python -m technology_park_abm.experiments E2 --seeds 1 2 3 4 5 --periods 120 --output results/v200
```

Reference runs: `results/v200/E1-20261013T180905Z-89870d0`,
`E2-20261013T180905Z-89870d0`, `E2-20261013T180912Z-89870d0` (120 periods),
`E3-20261013T180905Z-89870d0`, `E4-20261013T180906Z-89870d0`,
`E5-20261013T180906Z-89870d0`, `E6-20261013T181013Z-89870d0` (binding;
`E6-20261013T180906Z-89870d0` superseded).
