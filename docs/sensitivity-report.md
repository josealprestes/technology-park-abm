# Sensitivity report

Sensitivity analysis of the calibrated defaults under v1.2.0 behavior. Seeds 1-3, 60 periods, means of final-period values. All values are simulation output; none are empirical claims. OAT is screening only; the Morris/Sobol global analysis is the main result (GSA literature: OAT cannot detect interactions and is scale-dependent).

## Baseline (seeds 1-3, 60 periods)

| Metric | Mean final value |
| --- | --- |
| active_startup_count | 16.33 |
| knowledge_total | 35.28 |
| innovation_count | 3.67 |
| capital_total | 1027.13 |

## One-at-a-time screening (relative to baseline)

| Variation | Active startups | Knowledge total | Innovations | Capital total |
| --- | --- | --- | --- | --- |
| burn_rate x0.5 | 0.98 | 0.95 | 1.09 | 1.06 |
| burn_rate x1.5 | 0.96 | 0.94 | 1.27 | 1.00 |
| congestion_cost_per_org x0.5 | 1.27 | 1.37 | 1.27 | 1.37 |
| congestion_cost_per_org x1.5 | 0.88 | 0.80 | 1.27 | 0.89 |
| entry_reputation_weight x0.5 | 0.98 | 1.02 | 1.36 | 1.06 |
| entry_reputation_weight x1.5 | 1.04 | 1.00 | 1.18 | 1.02 |
| initial_capital x0.5 | 0.78 | 0.63 | 1.00 | 0.42 |
| initial_capital x1.5 | 1.14 | 1.22 | 1.27 | 1.87 |
| knowledge_spillover_rate x0.5 | 0.98 | 0.77 | 1.00 | 1.01 |
| knowledge_spillover_rate x1.5 | 1.00 | 1.10 | 0.91 | 1.00 |
| partnership_compatibility_weight x0.5 | 0.98 | 0.88 | 1.00 | 1.02 |
| partnership_compatibility_weight x1.5 | 1.00 | 1.06 | 1.36 | 0.99 |

## Morris screening (12 parameters)

Elementary effects on knowledge_total; `mu* x range` is the range-normalized effect (fair across different parameter scales), `sigma/mu*` above 1 signals non-linearity or interaction.

| Parameter (range) | mu* x range (knowledge) | sigma/mu* | mu* x range (active) |
| --- | --- | --- | --- |
| voluntary_exit_probability (0-0.5) | 32.86 | 1.02 | 17.50 |
| entry_potential_per_period (1-4) | 8.53 | 1.37 | 6.50 |
| knowledge_rnd_gain (0.15-0.45) | 4.75 | 1.00 | 0.38 |
| partnership_attempts_per_startup (1-4) | 3.90 | 2.30 | 0.63 |
| entry_base_probability (0.025-0.075) | 3.59 | 1.24 | 1.88 |
| initial_capital (75-225) | 3.45 | 2.61 | 1.13 |
| knowledge_spillover_rate (0.1-0.3) | 3.09 | 1.06 | 0.63 |
| entry_reputation_weight (0.15-0.45) | 2.36 | 1.51 | 0.63 |
| partnership_compatibility_weight (0.15-0.45) | 1.91 | 1.64 | 0.50 |
| partnership_base_probability (0.075-0.225) | 1.03 | 1.34 | 0.38 |
| congestion_cost_per_org (0.5-1.5) | 0.82 | 2.65 | 0.50 |
| burn_rate (0.5-1.5) | 0.00 | 0.00 | 0.00 |

## Sobol indices (N=192, top-4 by range-normalized Morris)

| Parameter | S1 (knowledge) | ST (knowledge) | S1 (active) | ST (active) |
| --- | --- | --- | --- | --- |
| voluntary_exit_probability | 0.817 | 0.836 | 0.776 | 0.837 |
| entry_potential_per_period | -0.000 | 0.067 | 0.094 | 0.214 |
| knowledge_rnd_gain | 0.002 | 0.115 | -0.013 | 0.008 |
| partnership_attempts_per_startup | -0.020 | 0.033 | -0.016 | 0.003 |

Total-order indices sum to about 1.05 for both outputs (near 1, as expected); small negative first-order values are Monte Carlo estimator noise at this sample size, not physical effects. Selection for the Sobol stage used the range-normalized Morris ranking (using unnormalized mu* would over-select small-range parameters; an earlier N=64/N=192 run with the wrong selection is superseded by this one).

Estimator note (2026-10-22): the Sobol core now centers each output by the pooled mean over A, B, and all AB blocks before estimation (removing the known bias of the Sobol' 1993 first-order estimator for non-centered outputs — the same normalization SALib applies), uses population variance (ddof=0), and the Morris sigma uses the sample standard deviation (ddof=1), matching SALib and the Morris literature. Both estimator cores are cross-validated against SALib to machine precision on the Ishigami function (`tests/test_gsa_crosscheck.py`). First-order Sobol values and Morris sigma therefore shift slightly relative to reports generated before this change; total-order indices are unchanged. The table above predates the change and is kept as the historical record; regenerate with the commands under Reproducibility for current numbers.

## Seed convergence

Mean and dispersion of final outputs as the seed count grows (periods 60):

| Seeds | Knowledge mean | Knowledge stdev | Active mean | Active stdev |
| --- | --- | --- | --- | --- |
| 5 | 34.60 | 2.04 | 16.60 | 0.80 |
| 10 | 34.35 | 1.69 | 17.00 | 0.89 |
| 20 | 33.63 | 2.39 | 16.55 | 1.02 |
| 40 | 33.99 | 2.77 | 16.90 | 1.41 |

Means are stable from 5 seeds; dispersion estimates keep growing toward the population value as more seeds are added, so uncertainty intervals should use at least 20-40 seeds.

## Interaction check (two-way probe)

Around the baseline (congestion_cost_per_org 1.0 -> 0.5, knowledge_spillover_rate 0.2 -> 0.3):

| Output | Congestion halved | Spillover raised | Both | Interaction |
| --- | --- | --- | --- | --- |
| active_startup_count | +4.33 | 0.00 | +4.33 | 0.00 |
| knowledge_total | +12.93 | +3.47 | +14.87 | -1.53 |
| innovation_count | +1.00 | -0.33 | +0.33 | -0.33 |
| capital_total | +380.23 | -5.24 | +372.62 | -2.37 |

## History-matching pilot (V2-5)

Grid over the two dominant OAT parameters (`congestion_cost_per_org` in
[0.5, 1.5] x `initial_capital` in [75, 225], 5 levels = 25 points, seeds
1-2, 20 periods = 50 model evaluations), ruled against wide stylized bands
from the validation report: active startups in [3, 30], partnership ties in
[5, 80], knowledge total in [5, 60]. Implausibility is the band distance in
units of seed dispersion (floored); cutoff 3.0.

Outcome: 4 points ruled out, 21 not-ruled-out-yet. All four ruled-out points
combine high initial capital (>= 150) with low congestion cost (<= 0.75):
rich startups under cheap congestion accumulate knowledge beyond the band.
The default (1.0, 150.0) sits inside the NROY region. Bands are stylized, so
this establishes the method — deterministic (`history_matching` twice gives
byte-identical reports), budgeted (50 evaluations), reported — not a
calibration. Empirical targets arrive with restricted data (R4).

```bash
python -m technology_park_abm.sensitivity --seeds 1 2 --periods 20 --history-matching --output results/hm-pilot.json
```

## Interpretation

- Voluntary exit dominates variance in both knowledge (S1 0.82, ST 0.84) and population (S1 0.78, ST 0.84). Survival, not entry or diffusion, is the binding margin in this calibration.
- Entry potential and R&D gain have small but non-zero total-order contributions (0.07-0.12); spillover and partnership attempts are nearly negligible within their sampled ranges.
- Nearly every parameter has sigma/mu* above 1, so OAT effects are unreliable in isolation; the range-normalized Morris ranking plus Sobol totals are the defensible summary.
- OAT conclusions changed between v1.0.0 and v1.2.0 (for example, initial_capital looked dominant in v1.0.0 OAT but is mid-tier and interaction-heavy here), which is exactly why the GSA replaced it as the main result.
- Congestion remains a strong lever on population through OAT (+27% when halved) but its range-normalized Morris effect is small because the baseline sits below capacity.

## Reproducibility

```bash
python -m technology_park_abm.sensitivity --seeds 1 2 3 --periods 60
python -m technology_park_abm.sensitivity --seeds 1 2 3 --periods 60 --interaction congestion_cost_per_org 0.5 knowledge_spillover_rate 0.3
python -m technology_park_abm.sensitivity --seeds 1 2 3 --periods 60 --gsa morris --convergence
python -m technology_park_abm.sensitivity --seeds 1 2 3 --periods 60 --gsa sobol --gsa-samples 192 \
  --gsa-parameters voluntary_exit_probability entry_potential_per_period knowledge_rnd_gain partnership_attempts_per_startup
```

`tests/test_regression.py` pins golden trajectories so unintended behavior changes fail the suite.
