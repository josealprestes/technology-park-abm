# Data, calibration, and validation

## Data candidates

Potential sources include public registries of firms and startups, patent and publication data, investment databases, employment statistics, university technology-transfer records, and park-level administrative data.

## Calibration strategy

Begin with stylized calibration to reproduce qualitative patterns: entry, exit, partnership formation, concentration, and growth. Use empirical calibration only after the mechanisms and measurement definitions are stable.

## Validation

- **Internal validation**: invariants, conservation rules, reproducibility, and process-order tests.
- **Historical validation**: compare aggregate trajectories with observed parks where data are available.
- **Pattern-oriented validation**: reproduce stylized facts such as firm-size heterogeneity, survival distributions, and network clustering.
- **Sensitivity analysis**: identify parameters that materially alter conclusions.

## Cautions

Calibration is not proof of causality. Multiple parameter combinations may generate similar outcomes. All results must report uncertainty and model limitations.

## Phase F7 public data pipeline and empirical feasibility

### Pipeline

- `data/manifest.json` (versioned) is the source catalog: name, description, URL, license, filename, fields, status, SHA-256 checksum, and access timestamp per source. Raw files are written to `data/raw/` and are never committed (ADR 0004).
- `python scripts/fetch_public_data.py` downloads cataloged sources, records checksums and access dates, and skips catalog-only sources that require manual retrieval.
- `technology_park_abm.data_pipeline` provides the network-free helpers used by tests (`sha256_file`, `load_catalog`, `save_catalog`, `record_download`); the simulation itself performs no network access.

### Catalog (schema 1.1, as of 2026-10-22)

Every entry carries `legal_basis` and `personal_data` (contract in
`docs/data-contracts.md`; legal study in `docs/lgpd-microdata-study.md`,
ADR 0012).

| Source | Content | License | personal_data | Status |
| --- | --- | --- | --- | --- |
| worldbank_tech_exports_brazil | High-technology exports (% of manufactured exports) | World Bank Open Data, CC BY 4.0 | aggregated | downloaded |
| worldbank_patents_brazil | Patent applications by residents, Brazil | World Bank Open Data, CC BY 4.0 | aggregated | downloaded |
| brasilapi_cnpj_sample | Anchor-firm statistics from a real CNPJ sample | Public business registry (Lei 8.934/1994) | none | downloaded |
| ibge_pnadc_educacao_ocupados | PNAD Contínua 7107: employed by education level (2025) | IBGE open data | aggregated | downloaded |
| ibge_pnadc_rendimento_instrucao | PNAD Contínua 10376: mean monthly income by education (2025) | IBGE open data | aggregated | downloaded |
| ibge_pnadc_ocupados_idade | PNAD Contínua 7432: employed by age group (2025) | IBGE open data | aggregated | downloaded |
| ibge_cempre_pessoal_secao_cnae | CEMPRE 3421: employment and mean wage by CNAE 2.0 section (2021) | IBGE open data | aggregated | downloaded |
| ibge_demografia_nascimentos_sobrevivencia | Demografia das Empresas 9949: firm births and 1-5y survival by CNAE section (2021) | IBGE open data | aggregated | downloaded |
| inpi_bulk_patents | INPI bulk patent and trademark data | Brazilian open government data | personal | catalog-only (manual retrieval) |
| mte_rais_microdata | RAIS worker/establishment microdata (FTP bulk) | MTE/PDET terms | personal | catalog-only (out of scope, ADR 0012) |
| mte_novo_caged_microdata | Novo CAGED monthly worker-level movements (FTP bulk) | MTE/PDET terms | personal | catalog-only (out of scope, ADR 0012) |
| mte_caged_estatistico | CAGED Estatístico (PAINEL/VÍNCULO), MTE approval + password | MTE approval required | personal | catalog-only (out of scope, ADR 0004/0012) |

### Data contracts

`src/technology_park_abm/data_contracts.py` enforces, at the pipeline
edges (full contract in `docs/data-contracts.md`):

- catalog entries (schema 1.1): required fields including `legal_basis`
  and `personal_data`; a `personal` source can never be `downloaded`;
- canonical microdata CSV (`education, age, wage, skill`): per-row ranges
  validated by `empirical.load_microdata` before resampling;
- aggregate payloads: SIDRA `/values/` responses and processed
  `year`/`value` series are shape-checked right after download in
  `scripts/fetch_public_data.py`.

### Legal and ethical notes (LGPD/ANPD)

- Only public sources are cataloged; no credentials, private datasets, or personal identifiers are stored.
- The legal study (`docs/lgpd-microdata-study.md`) concluded that RAIS/CAGED worker microdata are personal data (LGPD art. 5º, I) whose research use would require a documented legal basis, minimization, security measures and potentially a RIPD; official aggregates cover the same calibration targets, so microdata are out of scope (ADR 0012).
- Firm-level or aggregated records are preferred; any future personal data requires a new ADR with a documented legal basis, minimization, and retention rules.
- Authenticated or restricted sources remain out of scope until a new ADR defines access and compliance (ADR 0004).

### Empirical calibration feasibility

Full agent-level empirical calibration and historical validation are currently infeasible with public data alone: there is no public, longitudinal, park-level dataset linking startups, ties, investments, hiring, and exits for technology parks. Available public series (macro R&D spending, patent counts, employment aggregates) can inform priors and sanity checks for trends, but not the agent mechanisms or network structure of this model. Accordingly:

- Calibration remains stylized (F5) and sensitivity-driven (F6).
- The pipeline exists so that, if restricted microdata or park administrative records become available with a legal basis, retrieval is reproducible and auditable.
- Any future empirical calibration must report uncertainty and cannot be interpreted as causal proof.

### Calibration targets (ODD+2D style)

If park-level or restricted microdata become available, calibration will target these patterns and observables, in order of feasibility:

| Target pattern | Observable in the model | Candidate data source | Acceptance criterion |
| --- | --- | --- | --- |
| Survival and turnover | cumulative survival, exits by type | firm registries (CNPJ/Receita), park administrative records | simulated survival curve within the historical confidence band |
| Entry dynamics | entries per period vs attractiveness | registry openings filtered by park address | direction and order of magnitude |
| Partnership network | density, clustering, degree centralization | technology-transfer records, co-patent or co-project data | qualitative pattern match (clustering > 0, density within range) |
| Knowledge and innovation | innovation events, knowledge proxies | patents, publications, R&D surveys | rank correlation across parks or over time |
| Investment | investment events and amounts | investment databases, development-bank and VC reports | event frequency within an order of magnitude |
| Congestion | costs and occupancy | park occupancy and rent data | saturation behavior (costs rising above capacity) |

Calibration order: structural patterns first (survival, entry, network), magnitudes second (investment, costs), because multiple parameter combinations can reproduce magnitudes (equifinality). All calibration results must report uncertainty and cannot be interpreted as causal proof.

### Data access paths

- Public: cataloged sources in `data/manifest.json` (macro trends only, already retrieved with checksums).
- Restricted: park administrative records or firm microdata under a legal basis (LGPD), retrieved with the same pipeline; no personal identifiers are stored.
- The pipeline (`scripts/fetch_public_data.py`, `technology_park_abm.data_pipeline`) accepts new catalog entries without code changes.
