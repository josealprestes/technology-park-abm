# Experiments

Protocols implemented by `src/technology_park_abm/experiments.py` (phase F4); run with `python -m technology_park_abm.experiments`.

## E1: Critical mass

Vary initial population and measure whether productive interaction and survival show a threshold.

## E2: Diversity and specialization

Compare concentrated, complementary, and unrelated sector mixes while holding population constant. Since v2.0.0 (V2-4), summaries also carry `quality_mean` (mean technology quality among survivors) and `innovation_cumulative`, the productivity-type outputs used to retest H2.

## E3: Anchor participation

Compare no anchor, passive anchor, active anchor, and multiple competing anchors.

## E4: Policy instruments

Compare entry subsidy, R&D subsidy, shared infrastructure, matchmaking, talent programs, and investment funds.

## E5: Congestion

Increase population while holding infrastructure fixed. Estimate the point where marginal benefits turn negative.

## E6: Resilience

Remove central firms or the funding source and measure recovery, network rewiring, and survival. Since v2.0.0 (V2-4) the central shock collapses the top `shock_nodes` firms by partnership degree (3 in the runner scenario), and funding is survival-relevant at defaults through `investor_burn_relief`, so the funding collapse propagates to survival.

## E7: Distributedness and resilience (H6)

Vary network distributedness and measure recovery from a central-agent departure, which is what H6 actually states (E6 varied shock presence, not distributedness). The distributedness axis is `partnership_reputation_weight`: `hub` (0.6) lets reputation concentrate ties on few startups; `distributed` (0.0) forms ties on sector compatibility alone, spread across four sectors. Both scenarios take the same central-firm shock (top 3 by partnership degree) at mid-horizon with survival-relevant funding.

The shock fires during the step that ends at `shock_period`, so the last pre-shock record is period `shock_period - 1`. For every scenario with a shock (E6 and E7), `summary.json` adds, per scenario:

- `recovery_<metric>` for `active_startup_count`, `partnership_tie_count`, and `knowledge_total`: final value divided by the pre-shock baseline, per seed (distribution across seeds).
- `recovery_90pct`: 0/1 indicator of recovering at least 90% of pre-shock active startups; its mean is the share of seeds that recover.
- `baseline_degree_centralization`: the pre-shock network structure, the distributedness marker for the H6 contrast.

## Protocol

Each parameter combination should run across multiple seeds. Store configuration, seed, model version, metrics, and summary statistics. Report distributions, not just a single trajectory. Summary distributions carry `count`, `mean`, `min`, `max`, `median`, `q1`, `q3`, `p10`, and `p90`; quantiles use the inclusive method (linear interpolation, matching `numpy.percentile` defaults), so p10/p90 always stay within [min, max].

Independent (scenario, seed) runs can be parallelized with `--jobs N` (process pool); rows are assembled in deterministic scenario/seed/period order, so results are identical for any `jobs` value. Trend detection over a run is available through the Mann-Kendall test with Sen's slope (`mann_kendall_trend` and `marginal_output_trend` in `src/technology_park_abm/metrics.py`): a significant increasing trend in marginal output per additional agent is the statistical signature of increasing returns.
