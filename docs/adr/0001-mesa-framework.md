# ADR 0001: Adopt Mesa as the modeling framework

- Status: accepted
- Date: 2026-10-06

## Context

The project needs discrete-period agent-based simulation with heterogeneous agents, ordered processes, dynamic networks, and reproducible randomness. The initial engine (`src/technology_park_abm/model.py`) is intentionally minimal. `docs/architecture.md` anticipated replacing it with Mesa once scheduler, spatial, or analysis features were required. The repository owner selected Mesa over staying with the standard library.

## Decision

Adopt Mesa (`mesa>=3.5,<4`, runtime dependency in `pyproject.toml`) as the simulation engine while preserving the project's invariants:

- Deterministic execution with a supplied seed, implemented with explicit RNG streams.
- A fixed, documented scheduler order matching the ten-step order in `docs/architecture.md`.
- A thin facade so tests and experiment runners use stable entry points.
- Python requirement raised to >=3.12, matching Mesa's support floor.

The hand-rolled skeleton remains in place until the Mesa model lands in phase F1; behavior must not change silently.

## Consequences

- Mesa brings numpy, pandas, scipy, tqdm, and (in practice) networkx transitively; CI installs them.
- `networkx` is a declared runtime dependency because Mesa 3.5.1 imports it at package import time even though its metadata lists it only under the `network` extra. It will also back network metrics planned for F3.
- Visualization extras are not adopted now.
- Reproducibility tests and deterministic regression tests are mandatory guards against framework changes.
- Python 3.10 and 3.11 are no longer supported.

## Alternatives considered

- Pure standard library (previous state): full control and zero dependencies, but reinvents scheduling, data collection, and analysis at scale.
- Standard library plus networkx: better network analysis, but still a hand-rolled scheduler and collectors.
- Other simulation frameworks: weaker fit for a synchronized discrete-period model with explicit process order.
