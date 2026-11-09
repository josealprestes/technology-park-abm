# ADR 0011: LLM-agents policy — no online LLM in the model; offline and opt-in only

- Status: accepted
- Date: 2026-10-22

## Context

LLM-driven agents are a 2026 trend in agent-based modeling. This project has
hard invariants that constrain the option space: the model performs no
network calls (ADR 0004, gate G8), randomness is reproducible from a single
seed with no global or wall-clock sources (gate G7), and runs must be
byte-identical reproducible (gate G6). An online LLM call inside an agent's
step would violate all three: it is a network call, it is non-deterministic,
and it cannot be reproduced from a manifest.

Separately, AI coding agents (including the one that maintains this
repository) are already part of the development workflow, which raises the
question of what role LLMs may play in the artifact itself.

## Decision

1. **No online LLM calls from the model, dashboard, experiments, sensitivity
   runners, or tests — ever.** This is a standing rule, not a default that
   can be flipped by a parameter.
2. **LLM-assisted agent behavior is allowed only as an opt-in, offline,
   deterministic mechanism.** Concretely, either:
   - a locally hosted model invoked with a fixed seed and recorded
     configuration, or
   - precomputed LLM outputs committed as versioned input data with
     provenance, license, and checksums (treated exactly like any other
     input under ADR 0004).
   The default for any such mechanism is **off** (`none`/`baseline`), and
   golden trajectories must not depend on it.
3. **Reproducibility contract:** same seed and inputs must produce the same
   behavior. Any LLM-assisted mechanism must record its model, version,
   prompt template, and seed in the run manifest (ADR 0003), or it does not
   ship.
4. **AI coding agents may assist development** under the normal workflow:
   spec-first increments, gates G1-G15, docs traveling with code. AI-generated
   text in docs is reviewed by the author; simulation outputs are never
   presented as empirical facts, with or without AI assistance.
5. **No AI-generated content as data:** prompts, completions, or embeddings
   produced by an LLM may enter the repository only through the data
   pipeline's rules (public or licensed sources, checksums, no personal
   data — ADR 0004, LGPD).

## Consequences

- Gates G6/G7/G8 remain green by construction; a future "LLM agents"
  experiment (e.g., an E8 comparing scripted vs. LLM-assisted decision
  policies) must comply with rules 1-3 or it does not merge.
- The policy is checkable: `tests/test_gates.py` already scans `src/` for
  network and unseeded-randomness patterns; any future LLM mechanism must
  keep those scans passing.
- Reviewers can reject an LLM-related proposal by pointing at this ADR
  instead of re-litigating the trade-offs.

## Alternatives considered

- Allow online LLM calls behind an opt-in flag: rejected — it breaks
  determinism and the no-network rule, and "opt-in" flags drift toward
  being enabled in demos.
- Ban LLMs from the repository entirely (including development tooling):
  rejected — the development workflow already benefits from AI assistance,
  and the invariants that matter (determinism, no network, reproducibility)
  are about the artifact, not the tooling.
