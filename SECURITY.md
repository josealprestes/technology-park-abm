# Security policy

## Scope

`technology-park-abm` is an exploratory research simulator intended for
local use. This policy covers the code and dependencies distributed in
this public repository.

- **Offline model:** simulation, experiments and sensitivity analysis do
  not require network access. Installing dependencies and explicitly
  running public-data retrieval scripts require network access.
- **Local workbench:** `scripts/serve_investigation_prototype.py` binds
  `127.0.0.1` (default port 8777). Its HTTP API has no authentication or
  user isolation. Keep it local; do not expose it through port forwarding,
  tunnels or a public reverse proxy. Loopback binding and request-origin
  checks are not substitutes for authentication.
- **Public-data retrieval:** scripts use the catalog in
  `data/manifest.json`, validate supported payloads and record SHA-256
  hashes for reproducibility. A recorded hash does not independently
  establish the authenticity or safety of a download.

## Supported versions

The supported public version is **1.0.0**, as declared in `pyproject.toml`.
Security fixes are maintained on `main`; use its latest revision. Earlier
revisions are not maintained separately. Version numbers from other
repositories or internal development lines do not define support here.

## Reporting a vulnerability

Report suspected vulnerabilities privately to **contato@joseprestes.com**
with the subject prefix `[security] technology-park-abm`. Please include:

- a description of the issue and its security impact,
- the exact steps or input that trigger it,
- the environment (OS, Python version, package version, commit).

The target acknowledgment time is 7 days; a fix timeline depends on impact
and complexity. Please use this private channel first so disclosure can be
coordinated. Do not put exploit details, credentials or personal data in a
public issue. Use minimal synthetic examples when possible.

If you discover exposed credentials, report their location without copying
the secret. The credential owner should revoke or rotate them promptly;
removing them from a file or Git history alone is insufficient.

## Data protection notes

- Do not commit secrets, private datasets, raw downloads or worker-level
  microdata. Data ingestion is restricted to public statistical aggregates
  and permitted public company records (ADRs 0004 and 0012).
- Review exported JSON/CSV before sharing: they contain configurations,
  seeds, software versions and source provenance. Local execution does not
  make an export confidential or remove sensitive user-supplied values.
- Simulation outputs are labeled as simulation and are never presented as
  empirical facts.
