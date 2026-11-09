# ADR 0010: Mesa 4.x evaluation — stay on `mesa>=3.5,<4` and monitor

- Status: accepted
- Date: 2026-10-22

## Context

`pyproject.toml` pins `mesa>=3.5,<4` (ADR 0001). Mesa 4.0 is the announced
major release that promotes the new API introduced under `mesa.experimental`
in the 3.x series to the default and retires the legacy `mesa.Model` /
`mesa.Agent` surface. A 2026 research-software review asked whether the
project should prepare for or adopt Mesa 4.x.

Evaluation on 2026-10-22: the latest release on PyPI is **mesa 3.5.1**
(installed in `.venv`); no 4.x release (stable or pre-release) exists yet.
The actual Mesa surface used by the model is small:

- `src/technology_park_abm/model.py:15` — `from mesa import Model`;
  `TechnologyParkModel(Model[Any, Any])` with `super().__init__()` and
  `super().__init__(rng=config.seed)`.
- `src/technology_park_abm/agents.py:12` — `from mesa import Agent`;
  agent classes call `super().__init__(model)`.
- No `mesa.time` scheduler, no `mesa.space`, no Mesa visualization imports:
  the model implements its own ten-step order in `TechnologyParkModel.step()`
  (`docs/architecture.md`), so stepping semantics are ours, not Mesa's.
- `manifest.py` records `mesa_version` in every run manifest (ADR 0003).

## Decision

- Keep `mesa>=3.5,<4`. Do not adopt a 4.x pre-release; the upper bound stays
  until a deliberate migration ADR supersedes this one.
- Monitor: re-evaluate when Mesa 4.0 is released (check at each project
  release and at least quarterly), using the migration checklist below.
- Migration checklist for Mesa 4.0 (pre-agreed, small surface):
  1. Read the 4.0 migration guide; confirm the fate of `mesa.Model`,
     `mesa.Agent`, and the `rng=` constructor argument.
  2. Swap the two base-class imports to the 4.x API; keep the project's own
     ten-step `step()` unchanged.
  3. Run the full battery: `python scripts/run_checks.py` plus
     `pytest -m regression` (golden trajectories) and `pytest -m e2e`
     (byte-identical reproduction, gate G6). Any golden change caused by the
     framework (not by a deliberate model change) is a red flag: stop and
     investigate before updating goldens.
  4. Record the migration in a new ADR that supersedes this one, with the
     observed `mesa_version` in the manifest as evidence.

## Consequences

- The `<4` upper bound remains a deliberate, documented constraint, not an
  accident of neglect.
- Because the model owns its stepping order and uses only the two base
  classes, the expected migration cost is low; the golden-trajectory and
  reproduction gates (G5/G6) are the safety net that makes it safe.
- Reproducibility is preserved: manifests already record the exact Mesa
  version per run, so a future migration is auditable.

## Alternatives considered

- Adopt Mesa 4.x pre-release now: rejected — no release exists, and
  pre-release churn would put determinism and the golden gates at risk.
- Drop the upper bound (`mesa>=3.5`): rejected — a silent major upgrade could
  change RNG behavior or base-class semantics and break byte-identical
  reproduction (G6) without a deliberate decision.
- Vendor or fork Mesa: rejected — disproportionate for a two-import surface.
