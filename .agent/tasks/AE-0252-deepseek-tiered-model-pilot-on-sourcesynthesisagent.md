# AE-0252 — DeepSeek tiered-model pilot on SourceSynthesisAgent

Status: Intake
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Pilot DeepSeek on the `SourceSynthesisAgent` (research/extraction phase) via a
deterministic phase→model map, with Langfuse model + primary/fallback tagging, an
A/B parity check vs the ≥70 persona gate before committing, and a mandatory integration
test of JSON/structured-output + tool-calling through the endpoint — keeping Claude on
the voice surface.

## Problem

Every carousel phase runs on Claude Sonnet (one model seam:
`carousel_editorial_orchestrator.py:42-52` ← `container.llm_service().chat_model`).
Token-heavy, low-voice phases (research/source synthesis) pay Claude rates for no voice
benefit. DeepSeek is materially cheaper and adequate for extraction, but **must never
touch the voice surface** (content/caption/persona), where a regression fails the ≥70
persona gate = product failure. Two execution traps from the skeptical pass: (1) using
`.with_fallbacks([claude])` as the **tier boundary** makes cost + quality unmonitorable
(you pay both on degradation; Claude grades Claude = circular signal) — use a
deterministic phase→model map instead, with an explicit logged escalation path; (2)
`source_synthesis_agent.py:55-68` **hard-fails `ERR_INVALID_JSON`** with no graceful
degrade, so JSON/structured-output + tool-calling through the chosen endpoint MUST be
integration-tested before commit.

Evidence: ADR-0014 (tiered model selection; Proposed); arch-plan §13.1–§13.3;
skeptical-corrections.md §4. **Production DeepSeek sourcing is an OPEN decision** (Zen
gateway vs direct `api.deepseek.com`).

## Scope

- A deterministic phase→model map (resolved at orchestrator construction): research/
  source-synthesis → DeepSeek; content/caption/persona enforce + gate → Claude
  (unchanged).
- Pilot endpoint via the opencode Zen "Go" gateway (`https://opencode.ai/zen/go/v1`,
  `deepseek-v4-flash`) using `ChatOpenAI(base_url=…)`; production sourcing left OPEN.
- Langfuse tagging: `model_provider` + a primary/fallback flag on every call (cost +
  actual fallback-rate observable).
- An A/B parity harness comparing DeepSeek vs Claude on the research phase against the
  persona/quality bar; commit the phase to DeepSeek only if parity holds.
- An integration test of JSON/structured-output + tool-calling through the endpoint.

## Non-Goals

- Do **not** use `.with_fallbacks([claude])` as the tier boundary (it makes cost +
  quality unmonitorable). An explicit, logged, counted escalation path on DeepSeek
  failure is allowed — but it is not the invisible tier mechanism.
- Do not let DeepSeek touch content/caption/persona phases (voice surface) — confine it
  by injection point.
- Do not commit a phase to DeepSeek without the A/B parity check passing the ≥70 gate.
- Do not decide production sourcing here (OPEN: Zen vs direct DeepSeek API) — gate Zen to
  dev/pilot pending ToS/SLA/data-residency review.
- Do not pilot `QualityAgent` here (candidate, deferred until its prompt is on-registry).

## Acceptance Criteria

- [ ] A deterministic phase→model map drives selection (chosen before invocation); the
      research/source-synthesis phase resolves to DeepSeek, voice phases to Claude. No
      `.with_fallbacks` tier boundary.
- [ ] Every model call is Langfuse-tagged with `model_provider` + a primary/fallback
      flag; the actual fallback rate is observable.
- [ ] **Integration test:** JSON/structured-output + tool-calling through the chosen
      endpoint succeeds; a malformed-JSON case is exercised against the
      `source_synthesis_agent.py:55-68` hard-fail path (proving the integration was
      validated, not assumed).
- [ ] **A/B parity:** a documented A/B comparison of DeepSeek vs Claude on the research
      phase against the ≥70 persona/quality bar exists; the phase is committed to
      DeepSeek **only if parity holds** (else it stays on Claude with the finding
      recorded).
- [ ] Production sourcing is recorded as an OPEN decision (Zen vs direct API); the Zen
      gateway is dev/pilot-only pending governance review.
- [ ] Backend `pytest`/`mypy`/`ruff` green.

## Gherkin Scenarios

> Behavior-changing (a phase changes model provider; cost + output characteristics
> shift), so a `.feature` IS required — happy + edge + failure.

```gherkin
Feature: Tiered model selection pilots DeepSeek on the research phase

  Scenario: The research phase resolves to DeepSeek; voice phases stay Claude
    Given the deterministic phase to model map
    When the orchestrator is constructed
    Then source synthesis resolves to DeepSeek
    And content, caption, and persona phases resolve to Claude

  Scenario: Structured output is validated through the endpoint
    Given the DeepSeek endpoint is used for source synthesis
    When the agent requests JSON/structured output and tool calls
    Then the response parses successfully in the integration test

  Scenario: A phase is not committed to DeepSeek without parity
    Given an A/B comparison of DeepSeek vs Claude on the research phase
    When DeepSeek fails the >=70 persona/quality parity bar
    Then the phase stays on Claude and the finding is recorded
```

## Delta

### ADDED

- A deterministic phase→model map + DeepSeek endpoint wiring (Zen, dev/pilot).
- Langfuse `model_provider`/primary-fallback tagging.
- A/B parity harness + the JSON/tool-calling integration test.

### MODIFIED

- The carousel model seam (`carousel_editorial_orchestrator.py` model selection) to read
  the phase→model map; `source_synthesis_agent.py` to use the mapped model.

### REMOVED

- None.

## Affected Areas

- Backend: model-selection map, `carousel_editorial_orchestrator.py`,
  `source_synthesis_agent.py`, LLM client wiring.
- Frontend: none.
- Database: none.
- API: none.
- Tests: JSON/tool-calling integration test + phase-map unit test + A/B harness.
- Docs: ADR-0014 reference; the OPEN production-sourcing decision.
- Prompts/LLM: research phase uses DeepSeek; voice phases stay Claude.
- Observability: Langfuse `model_provider` + primary/fallback tags (cost attribution).
- Deployment: a DeepSeek endpoint secret/config (GitHub Secret per the prod-env pattern);
  Zen dev/pilot-only.

## Dependencies

- Provisional epic id: **RES-13** (DeepSeek pilot; after Phase 1).
- Gating ADR: **ADR-0014 (tiered model selection — DeepSeek)**; the production-sourcing
  sub-decision stays OPEN.
- Blocked by: **AE-0243 (RES-5)** — don't bake a cheap model onto a hardcoded prompt
  (the quality phase must be on-registry first; the research seam benefits from the
  registry move too).
- Blocks: none (a pilot; broadening to `QualityAgent` is a follow-up).
- Related: AE-0248 (RES-9) — the harness `DeepAgentConfig` can later carry the per-role
  model map; this pilot wires the carousel seam directly first.

## Implementation Plan

1. Add the deterministic phase→model map; wire the research/source-synthesis seam to a
   DeepSeek `ChatOpenAI(base_url=…)` client (Zen "Go", dev/pilot).
2. Add Langfuse `model_provider` + primary/fallback tagging.
3. Write the JSON/structured-output + tool-calling integration test (incl. the
   malformed-JSON hard-fail path); confirm the endpoint handles structured output.
4. Run the A/B parity harness vs the ≥70 gate; commit the phase to DeepSeek only if
   parity holds; record the OPEN production-sourcing decision.
5. Run gates.

## QA Checklist

- [ ] Security reviewed (routing user content through a third-party gateway — Zen
      dev-only; production sourcing OPEN)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (malformed JSON hard-fail path; parity-fail keeps Claude)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:30

Created from the agent-architecture-restructure epic (RES-13). Deterministic phase→model
map (NOT `.with_fallbacks` as the boundary); A/B parity vs ≥70 before commit; JSON/
tool-calling integration test mandatory; production sourcing OPEN.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **Deterministic phase→model map, not `.with_fallbacks` as the tier boundary.** A
  silent fallback makes cost + quality unmonitorable (pay both on degradation; Claude
  grading Claude = circular signal). An explicit, logged, counted escalation path is
  fine; the tier itself is deterministic (arch-plan §13.1, skeptical §4).
- **A/B parity vs the ≥70 persona gate before committing a phase** — moving a phase to a
  cheaper model must clear the quality bar, or it stays on Claude.
- **Integration-test JSON/tool-calling.** `source_synthesis_agent.py:55-68` hard-fails
  `ERR_INVALID_JSON` with no graceful degrade — DeepSeek structured-output fidelity
  through the endpoint is unverified, so it must be tested, not assumed.
- **Production sourcing is OPEN** (Zen vs direct DeepSeek API) — Zen gated to dev/pilot
  pending ToS/SLA/data-residency review; not mandated here.

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **Behavior-changing** — a phase changes model provider; cost and output
  characteristics shift. **`.feature` REQUIRED** (phase mapping; structured-output
  validated; parity gate before commit).
- **Affected gates:** backend `pytest`/`mypy`/`ruff` + the JSON/tool-calling integration
  test.

## Blockers

None (sequenced after AE-0243; production sourcing is an OPEN decision, not a blocker
for the pilot).

## Final Summary

Pending.
