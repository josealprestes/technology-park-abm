# Empirical calibration report

Status of the empirical layer after v2.0.0 (V2-3). Real, checksummed public data are now ingested and validated; full park-level calibration remains infeasible, as documented.

## V2-3: real worker marginals (2026-10-13)

Worker attribute tables are no longer placeholders. `empirical.py`
(`AGGREGATE_SOURCES`) now encodes, accessed 2026-10-13:

| Table | Values | Source |
| --- | --- | --- |
| Education shares | fundamental 13.8%, medio 55.0%, superior 31.2% | RAIS 2023 stock by schooling, MTE presentation (complete universe, 54.7M vínculos; 6-level chart grouped into 3) |
| Age shares (18-64) | 18-24: 13.4%, 25-34: 27.9%, 35-44: 27.0%, 45-54: 20.5%, 55-64: 11.2% | RAIS 2023 absolute stock by age band, MTE executive summary; renormalized over 18-64 with uniform splits of the 10-year bands |
| Wage bands (SM) | fundamental (1.2, 2.1), medio (1.4, 2.5), superior (3.2, 6.0) | PNAD Contínua means (fundamental R$2,535, medio R$2,905, superior R$6,947; 2025) and FGV IBRE Oct 2024 (+126% superior premium); midpoints track the published means |

Joint pattern guarded by T17 tests: marginals within ±0.02, mean age in
(37, 40), wage ratios superior/medio in (1.8, 3.2) and medio/fundamental in
(1.0, 1.5) — matching the published ~2.4x and ~1.15x premiums. Only
`empirical_init` modes change; defaults (`none`) are untouched, so golden
trajectories are unaffected. Size-class and research-quality tables remain
stylized. A technology park workforce would skew more schooled than the
national formal stock; that selection effect is modeled nowhere and stays a
limitation. For built-in aggregate constants the code version plus git
commit (already in every manifest) is the data snapshot identifier.

## Real data ingested (validated, checksummed)

| Source | Content | Coverage | Use in the model |
| --- | --- | --- | --- |
| BrasilAPI CNPJ sample (`brasilapi_cnpj_sample`) | 10 large Brazilian firms: porte, capital social, age, CNAE | real company registry sample, aggregated output only | anchor capital drawn log-uniform in the real range (R$ 2.96-205.4 bn; median 14.2 bn; median age 43 years) |
| World Bank patents (`worldbank_patents_brazil`) | Patent applications by residents, Brazil | 66 annual observations | macro innovation context and calibration sanity checks |
| World Bank high-tech exports (`worldbank_tech_exports_brazil`) | High-technology exports (% of manufactured exports), Brazil | 18 observations, latest 2024 = 11.11% | macro context for the private-sector playbook |
| World Bank R&D expenditure | `GB.XPD.RSD.GD.ZS` | **invalid**: the World Bank API now rejects the indicator | source removed and replaced; the pipeline now rejects API error payloads |

The broken R&D source was detected during this work: the downloaded file contained an API error message while a checksum had been recorded. The pipeline (`scripts/fetch_public_data.py`) now validates World Bank payloads (error messages, empty or all-null observations) before recording a download, and the catalog was corrected (`data/manifest.json`).

## What the real data changes

- Anchor firms created with `empirical_init != "none"` draw capital from the real sample range (log-uniform), replacing the fixed placeholder; anchor capital is informational and does not drive mechanisms.
- Sector profiles and connection priors remain documented placeholders inspired by CAGED/RAIS/PNAD aggregates; worker attribute tables are real published marginals since V2-3 (above). Microdata require large manual extracts (FTP, hundreds of MB per year) and stay outside version control (ADR 0004). The canonical CSV loader (`education, age, wage, skill`) is ready for extracts.
- CNAE-inspired sector proximity and the university-industry co-patent proxy are implemented as documented priors, not estimated from data.

## Calibration playbook status

| Target | Status | Evidence |
| --- | --- | --- |
| Anchor size/capital distribution | real sample ingested | `data/manifest.json` `brasilapi_cnpj_sample` summary |
| Macro innovation trend | real series ingested | patents and high-tech exports above |
| Worker composition (education, age, wage) | real RAIS/PNAD marginals + joint-pattern tests | `empirical.py` `AGGREGATE_SOURCES`, `tests/test_empirical.py` T17 |
| Entry/exit/hiring flows by sector | documented multipliers | `docs/playbooks.md` |
| Connection timing | model-side metrics (`ties_formed_by_type`) | E6 tests and dashboard markers |
| Park-level historical validation | infeasible with public data | `docs/data-and-calibration.md` feasibility assessment |

## Limitations

- The CNPJ sample is a convenience sample of large firms (all `DEMAIS` porte), not representative of park demographics.
- No public, longitudinal, park-level dataset links startups, ties, investments, and exits; historical validation remains out of reach.
- Microdata ingestion, if extracts become available, must follow LGPD and ADR 0004 (no raw data in git; checksummed manifests only).

## Reproduce

```bash
python scripts/fetch_public_data.py                                   # validated downloads + checksums
python scripts/build_empirical_profiles.py                            # real CNPJ sample -> aggregates
python -m technology_park_abm.dashboard                                # empirical modes under "Dados empíricos"
python -m technology_park_abm.experiments E3 --seeds 1 2 3 --periods 60
```
