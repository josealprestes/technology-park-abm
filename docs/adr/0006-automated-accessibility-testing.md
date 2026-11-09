# ADR 0006: Automated accessibility testing with Playwright and axe

- Status: accepted
- Date: 2026-10-13 (explicit user approval; supersedes the deferred proposal in `docs/ux-plan.md`)

## Context

UI/accessibility was enforced only by static contract tests (T12) plus a
manual checklist. The `web-dashboard-ux` skill calls for automated rules
(axe) alongside keyboard sweeps and task-based checks, but that tooling was
deferred for lack of dependency approval.

## Decision

- Add `playwright` and `axe-playwright-python` as **dev-only** dependencies
  (no runtime change; the dashboard stays dependency-free per ADR 0005).
- Cover, in headless Chromium against the loopback server
  (`tests/test_a11y_browser.py`, `pytest -m a11y`):
  zero console errors, zero axe violations, keyboard reachability of primary
  actions, the welcome→tour→nudge journey, and tour-checklist persistence.
- Browsers are environment-provided (`python -m playwright install
  chromium`); the fixture fails with that actionable message when missing
  instead of skipping silently. CI installs Chromium and runs the suite.
- axe findings are fixed at the cause (first run: heading order + landmark
  region, fixed the same day), never baselined as accepted violations.

## Consequences

- `pip install -e ".[dev]"` gains two packages; fresh checkouts also run
  `python -m playwright install chromium` (documented in `docs/handoff.md`).
- A red automated-a11y gate is fixed like any other gate (G12 in
  `AGENTS.md`); task-based checks (SUS, time-to-first-insight) stay manual.
