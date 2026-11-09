# ADR 0013: 2026 toolchain — uv lockfile, ty + pyrefly alongside mypy, cosmic-ray for distributed mutation testing

- Status: accepted
- Date: 2026-10-22

## Context

A 2026 research-software review of the development toolchain found four
gaps:

1. **No lockfile.** `pyproject.toml` declared version ranges
   (`mesa>=3.5,<4`, `pytest>=8,<10`, ...) but nothing pinned the full
   transitive closure. Two contributors (or CI and a laptop) could resolve
   different dependency versions and get different behavior, which is
   exactly the class of drift the reproducibility gates (G5/G6) exist to
   catch.
2. **One type checker.** `mypy --strict` was the only static type check.
   mypy is excellent but a single checker shares its blind spots; the 2026
   Python type-checking landscape offers two additional checkers written in
   Rust (`ty` by Astral, `pyrefly` by Meta) that are fast enough to run on
   every local check and catch different classes of errors.
3. **mutmut config was broken.** `[tool.mutmut]` used the deprecated
   `paths_to_mutate` key and `tests_dir = "tests"` as a string; mutmut 3.8.0
   crashed with `TypeError: can only concatenate list (not "str") to list`
   before testing a single mutant. The mutation step in
   `scripts/run_checks.py --full` was dead code.
4. **No distributable mutation runner.** mutmut runs mutants sequentially on
   one machine. For a weekly mutation-score review (target >= 70%, see
   `docs/test-plan.md`) and for CI, a runner that can distribute work across
   processes/machines is the standard 2026 answer.

## Decision

- **Lockfile: `uv`.** Add `uv.lock` (committed) generated with `uv lock`.
  `uv sync --extra dev` reproduces the full dev environment byte-for-byte
  from the lock. The classic `python -m venv && pip install -e ".[dev]"`
  workflow keeps working (documented in `AGENTS.md` and
  `docs/contributing.md`) for contributors who prefer pip, including
  Windows. `uv` is a dev-environment tool only; it is not a runtime
  dependency and the model still performs no network calls.
- **Type checking: mypy stays the strict gate; ty and pyrefly join as
  additional checkers.** `scripts/run_checks.py` runs, in order:
  `ruff check`, `ruff format --check`, `mypy` (strict, unchanged),
  `ty check src tests scripts`, `pyrefly check src tests scripts`. All five
  must be green. mypy remains the source of truth for the `strict` gate
  (G3); ty/pyrefly are additional nets, not replacements.
- **Mutation testing: mutmut (local) + cosmic-ray (distributed).**
  - mutmut stays the local battery step (`run_checks.py --full`). Its
    config in `pyproject.toml` is fixed: `source_paths` (the three pure-logic
    modules `network.py`, `metrics.py`, `validation.py`), `also_copy = ["src"]`
    (the mutants tree must be a complete, importable package — without it
    `mutants/src/technology_park_abm/` holds only the three mutated files and
    sibling imports fail during the stats run), and a test selection of the
    19 in-process test files that exercise the scoped modules directly or
    through the model. Browser/server/gate/data tests are deliberately
    excluded: the stats run must pass cleanly inside the mutants tree, and
    mutmut's parallel workers would make port-bound tests falsely kill
    mutants. mutmut 3.8 runs a stats pass that associates each mutant with
    only the tests that execute the mutated function, so the local run is
    tractable (388 mutants in ~35 s on 4 cores).
  - cosmic-ray 8.x is added as the config-driven, distributable runner.
    `cosmic-ray.toml` (committed) scopes the same three modules and runs the
    full suite per mutant; the `http` distributor spreads work across
    workers for CI. cosmic-ray is deliberately NOT in the local battery:
    running the full suite per mutant sequentially would double local
    runtime for no extra local information.
- **Dev-only dependencies.** `ty`, `pyrefly`, and `cosmic-ray` are added to
  the `dev` extra only. They never become runtime dependencies (repo rule:
  no new dependencies without a pyproject update and a recorded reason —
  this ADR is that record).

## Consequences

- Reproducibility improves: `uv.lock` pins 82 packages; a fresh
  `uv sync --extra dev` was verified to install, import the package, and
  collect all 413 tests.
- The type-check net is wider: adopting ty/pyrefly surfaced and fixed 12
  real diagnostics (TypedDict narrowing after `model.advance()`, implicit-Any
  returns in `agents.py`, an untyped list in `scripts/verificar_arestas.py`,
  and a `dict[str, object]` that blocked `**` unpacking in a test). Two
  targeted `# ty: ignore[...]` suppressions document a Mesa 3.x stub quirk
  (`Model.step` read as a union) at `model.py:317` and `model.py:341`; mypy
  is unaffected because it does not parse `ty:` directives.
- The mutation step is alive again: `run_checks.py --full` runs mutmut to
  completion and prints results. Measured 2026-10-22 on the scoped modules:
  388 mutants, 315 killed, 73 survived, 0 without tests — **mutation score
  81.2%** (killed / (killed + survived)), above the >= 70% target. The
  survivors concentrate in `mann_kendall_trend` boundary branches (e.g. the
  `count < 2` guard) and in error-message string mutations; both classes are
  recorded as follow-up in `docs/test-plan.md`.
- cosmic-ray was validated end-to-end: `cosmic-ray init` builds 1074
  mutation work items over the three scoped files and `cosmic-ray baseline`
  passes (test command works on unmutated code).
- Contributors need either `uv` (recommended, lockfile-exact) or the
  existing venv+pip flow; both are documented. No contributor is forced to
  install Rust-based tools unless they run the local battery, and the
  battery degrades gracefully (each step reports independently).

## Alternatives considered

- **pip-tools / poetry / hatch for locking**: rejected — `uv` produces a
  single committed `uv.lock` with a fast resolver and a drop-in
  `uv sync`, without changing the build backend (setuptools stays).
- **Replace mypy with ty or pyrefly**: rejected — mypy `--strict` is the
  project's documented gate (G3) with years of accumulated config; the new
  checkers complement it. Replacing would churn every suppression and
  weaken the gate's meaning.
- **Run cosmic-ray locally instead of mutmut**: rejected — cosmic-ray runs
  the full suite per mutant (1074 mutants x ~1 min = hours single-threaded);
  mutmut's per-mutant test selection makes the local run minutes. cosmic-ray
  is for distributed/CI execution where parallelism compensates.
- **Widen the mutation scope beyond the three modules**: rejected for now —
  the scope is deliberate (pure logic, densest unit coverage, tractable
  runtime). Widening is a separate decision that should follow a measured
  score on the current scope.
