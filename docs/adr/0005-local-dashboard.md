# ADR 0005: Local calibration dashboard without new dependencies

- Status: accepted
- Date: 2026-10-07

## Context

The project needs a visual, NetLogo-like way to inspect and calibrate simulation parameters. Mesa's official visualization stack (SolaraViz) would add the `solara`, `altair`, and `matplotlib` dependencies, is harder to test headlessly, and still requires a custom component for the typed network. The repository favors minimal dependencies, determinism, and testable components.

## Decision

- Ship a local web dashboard built only on the standard library plus the existing `networkx` dependency (used for deterministic graph layout).
- The dashboard binds to loopback by default (`127.0.0.1`), is a UI layer over the same `TechnologyParkModel`, and never changes model semantics or the metrics contract.
- Parameter controls are generated from the `ModelConfig` and `Policy` dataclasses; a coverage test guarantees every field is exposed.
- Network positions come from a seeded spring layout and are visual only, never model state.
- Output remains simulation-only and is never presented as empirical evidence.

## Consequences

- `python -m technology_park_abm.dashboard` serves the UI with Apply/Reset, Step, Play/Pause controls, live metric charts, and the network view.
- No new runtime dependencies; CI exercises the dashboard through loopback HTTP tests.
- SolaraViz remains an option for later if polished widgets outweigh the dependency cost.
