# Data contracts

Machine-checkable contracts for the three artifacts that cross the data
pipeline boundary. The validators live in
`src/technology_park_abm/data_contracts.py` (standard library only, no
network access) and are enforced at the pipeline edges: catalog loading
(`data_pipeline.load_catalog`), microdata loading
(`empirical.load_microdata`), and right after download
(`scripts/fetch_public_data.py`). The legal motivation is
`docs/lgpd-microdata-study.md` and ADR 0012.

## 1. Catalog entry contract (schema 1.1)

`data/manifest.json` carries `schema_version: "1.1"`. Every source entry
must satisfy `validate_catalog_entry`:

| Field | Rule |
| --- | --- |
| `name` | non-empty string, unique across the catalog |
| `description` | present |
| `url` | non-empty string |
| `license` | non-empty string (license or terms of use) |
| `filename` | string, required when `status` is `cataloged` or `downloaded` |
| `status` | one of `cataloged`, `catalog-only`, `downloaded` |
| `legal_basis` | non-empty string: the legal basis (or the explicit out-of-scope reason) for ingesting the source |
| `personal_data` | one of `none`, `aggregated`, `personal` (see below) |

Hard rule: a source with `personal_data: "personal"` must never have
`status: "downloaded"` — person-level records stay `catalog-only` until a
new ADR documents a legal basis (ADR 0012). The validator raises on this
combination, so the policy is enforced mechanically, not just documented.

`personal_data` taxonomy (LGPD art. 5º, I — "pessoa natural"):

| Level | Meaning | Examples in the catalog |
| --- | --- | --- |
| `none` | no personal data | CNPJ firm registry aggregates (legal entities), macro indicators without person breakdowns |
| `aggregated` | published statistical aggregates | SIDRA/IBGE tables, World Bank indicators |
| `personal` | person-level records | RAIS/CAGED worker microdata, INPI bulk records with holder/inventor names |

## 2. Canonical microdata contract

The microdata mode (`empirical_init="microdata"`) reads a canonical CSV
extract with exactly the columns `education, age, wage, skill`
(`empirical.MICRODATA_COLUMNS`). `validate_microdata_rows` enforces, per
row (line numbers count the header as line 1):

| Column | Rule |
| --- | --- |
| `education` | one of `fundamental`, `medio`, `superior` |
| `age` | integer in [18, 64] |
| `wage` | positive number (minimum wages) |
| `skill` | number in [0, 1] |

The file must contain at least one data row. Violations raise `ValueError`
with the line number, so a malformed extract never reaches the sampler.
The extract itself is produced outside the repository from an authorized
source; raw microdata is never committed (ADR 0004) and, per ADR 0012,
worker-level microdata is out of scope for this project.

## 3. Aggregate payload contracts

Two shapes are validated at fetch time:

- **SIDRA `/values/` payloads** (`validate_sidra_payload`): a JSON array
  whose first element is the header row (must contain `V` and `D1N`) and
  whose data rows carry `V` (value) and `D3N` (period). SIDRA suppresses
  unstable estimates with `"..."` and marks not-applicable cells with
  `"-"`; both sentinels are accepted, but at least one concrete value must
  be present. Applied to every catalog source whose name starts with
  `ibge_`.
- **Processed aggregate series** (`validate_aggregate_series`): a non-empty
  list of `{"year": int, "value": number | null}` records, where `null`
  marks a suppressed estimate. Used for World Bank and SIDRA-derived
  series in processed artifacts.

## Why contracts

- Fail fast at the boundary: a truncated, error-shaped, or
  contract-violating payload is rejected before it reaches `data/raw/` or
  the agent sampler.
- Make the legal policy executable: `legal_basis` + `personal_data` are
  required fields, and the personal-data download ban is a validator rule,
  not a convention.
- Keep the model network-free and deterministic: contracts are pure
  validation; they add no I/O and no randomness to the simulation.
