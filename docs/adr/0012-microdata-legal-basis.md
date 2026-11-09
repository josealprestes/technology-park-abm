# ADR 0012: Legal basis for microdata — aggregate-only ingestion

- Status: accepted
- Date: 2026-10-22

## Context

The agent-enrichment plan (`docs/agent-enrichment-plan.md`, E1-E4) considers
initializing agent attributes from RAIS/CAGED worker microdata. The legal
study `docs/lgpd-microdata-study.md` (LGPD Lei 13.709/2018, Decreto
8.777/2016, ANPD guidance, MTE terms) established that:

- RAIS/CAGED microdata are person-level records (LGPD art. 5º, I) and
  "de-identified" is not "anonymized" (ANPD 2024 risk-based standard);
- research use would require a documented legal basis (art. 7º, IX c/c
  art. 11º, II), minimization, security measures, a DPO, and potentially a
  RIPD (art. 10, § 3º);
- access is bulk-only via FTP (RAIS, Novo CAGED) or authenticated with MTE
  approval (CAGED Estatístico — already out of scope per ADR 0004);
- official aggregates (IBGE SIDRA) cover the same calibration targets
  (education, age, wage, firm size, entry and survival) without personal
  data.

## Decision

- Ingest only **official statistical aggregates** (IBGE SIDRA, World Bank)
  and **public registries of legal entities** (CNPJ). No worker-level
  microdata.
- RAIS, Novo CAGED and CAGED Estatístico are cataloged as `catalog-only`
  with `personal_data: "personal"` and the out-of-scope reason recorded in
  `legal_basis`.
- The catalog contract (schema 1.1, `data_contracts.py`,
  `docs/data-contracts.md`) requires `legal_basis` and `personal_data` on
  every source and **rejects** any source with `personal_data: "personal"`
  in `downloaded` status — the policy is enforced by validation, not only
  documented.
- Any future use of personal microdata requires a new ADR with a
  documented legal basis, RIPD, defined operator/DPO, and retention rules.

## Consequences

- Calibration uses SIDRA aggregates fetched with checksums (PNAD Contínua
  education/age/wage marginals; CEMPRE sector employment and wages;
  Demografia das Empresas entry and survival rates).
- The data pipeline stays network-light, auditable, and free of personal
  data; raw data remains gitignored (ADR 0004).
- The legal study is engineering analysis, not legal advice; it must be
  revisited if the scope changes.
