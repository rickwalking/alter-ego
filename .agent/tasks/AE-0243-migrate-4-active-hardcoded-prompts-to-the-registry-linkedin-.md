# AE-0243 — Migrate 4 active hardcoded prompts to the registry (linkedin/persona/quality)

Status: Intake
Tier: T2
Priority: High
Type: Refactor
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Move the 4 remaining **active** hardcoded prompts into the prompt registry so every
agent prompt is loaded via `agents.prompts.registry`, with byte-for-byte output
parity preserved (no behavior drift).

## Problem

Four live prompt strings are built inline instead of via the registry, violating the
CLAUDE.md "prompts live in `.md`/`.yaml`, never in `.py`" standard. The single most
concentrated offender is `quality_agent.py` — **0% on-registry today**:

| # | File:line | Inline prompt | Lines |
|---|-----------|---------------|-------|
| 1 | `application/services/linkedin_post_generator.py:148` | `_build_prompt()` f-string (300-char limit, no em-dash, hashtag rules) | 24 |
| 2 | `agents/persona_agent.py:88` | `_build_style_guide()` f-string (tone/sentence/forbidden-phrase rules) | 21 |
| 3 | `agents/quality_agent.py:53` | `_build_evaluation_prompt()` (rubric eval → JSON) | 17 |
| 4 | `agents/quality_agent.py:141` | `generate_improvement_suggestions()` f-string | 9 |

The registry standard already exists (`agents/prompts/registry.py:60,90`,
`get_system_prompt` / `render_prompt`) and 8 call sites comply — these 4 are the
holdouts. `persona_agent.py:_build_style_guide` is **parameterized** (persona name,
tone, forbidden phrases, writing samples) so it must become a Jinja2 `.yaml`, not a
flat `.md`.

Evidence: arch-plan §1.1 table rows #2–#5, §1.2 target file list. The DEAD
`TEMPLATE_ENFORCE` is **not** in scope here — it is deleted by AE-0242 (RES-4).

## Scope

- `application/services/linkedin_post_generator.py:148` → load
  `render_prompt("distribution", "linkedin_post", …)`.
- `agents/persona_agent.py:88` (`_build_style_guide`) → load
  `render_prompt("persona", "enforce", …)` (Jinja2; parameterized vars).
- `agents/quality_agent.py:53` (`_build_evaluation_prompt`) → load
  `render_prompt("quality", "evaluate", …)`.
- `agents/quality_agent.py:141` (`generate_improvement_suggestions`) → load
  `render_prompt("quality", "improve_suggestions", …)`.
- New prompt files under `agents/prompts/{persona,quality,distribution}/v1/*.yaml`
  plus per-domain README pointers (per arch-plan §1.2).

## Non-Goals

- Do **not** migrate `TEMPLATE_ENFORCE` (deleted in AE-0242).
- Do not change the prompts' wording/semantics — this is a relocation with byte-parity,
  not a rewrite.
- Do not remove the legit guarded fallback constants (`_FALLBACK_SYSTEM_PROMPT`,
  `_ALTER_EGO_FALLBACK_PROMPT`, `_JSON_REPAIR_PROMPT`); a 1-line fallback per migrated
  prompt is acceptable per arch-plan §1.1.
- Do not add the anti-hardcoded-prompt CI checker here — that is AE-0244 (RES-6).

## Acceptance Criteria

- [ ] The 4 call sites load their prompt via `agents.prompts.registry`
      (`render_prompt(...)`); no inline multi-line prompt string remains in those four
      functions.
- [ ] New registry files exist and render: `persona/v1/enforce.yaml` (Jinja2,
      parameterized), `quality/v1/evaluate.yaml`, `quality/v1/improve_suggestions.yaml`,
      `distribution/v1/linkedin_post.yaml`, each with a domain README pointer.
- [ ] **Golden-output parity:** a test renders each new registry prompt with the same
      inputs the old f-string used and asserts the result **equals** the legacy
      f-string output (whitespace/ordering identical) — proving behavior is preserved
      (arch-plan §12 "Prompt extraction parity risk").
- [ ] `quality_agent.py` has **zero** inline prompt strings afterward (it was 100%
      off-registry; it is now 100% on-registry).
- [ ] `uv run pytest` / `mypy` / `ruff` green.

## Gherkin Scenarios

> Behavior-preserving refactor; the contract under test is "registry output == legacy
> output". Classified as a refactor (no public behavior change) — the parity tests are
> the proof. No `.feature` required (AE-0153); golden-parity unit tests suffice.

```gherkin
Feature: Active prompts are loaded from the registry with output parity

  Scenario: Persona-enforce prompt renders identically from the registry
    Given the persona vars used by _build_style_guide
    When persona/v1/enforce.yaml is rendered with those vars
    Then the rendered text equals the legacy _build_style_guide output

  Scenario: Quality-agent prompts come only from the registry
    Given quality_agent builds an evaluation and an improvement prompt
    When those call sites run
    Then both prompts are loaded via render_prompt
    And quality_agent.py contains no inline prompt string
```

## Delta

### ADDED

- `agents/prompts/persona/v1/enforce.yaml` (+ README), `quality/v1/evaluate.yaml`,
  `quality/v1/improve_suggestions.yaml`, `distribution/v1/linkedin_post.yaml`.
- Golden-output parity tests under `backend/tests/`.

### MODIFIED

- `linkedin_post_generator.py`, `persona_agent.py`, `quality_agent.py` — call sites
  switch to `render_prompt`; inline strings removed (1-line fallback retained).

### REMOVED

- The 4 inline prompt f-strings.

## Affected Areas

- Backend: `agents/persona_agent.py`, `agents/quality_agent.py`,
  `application/services/linkedin_post_generator.py`, `agents/prompts/*`.
- Frontend: none.
- Database: none.
- API: none.
- Tests: golden-output parity tests.
- Docs: per-domain prompt READMEs.
- Prompts/LLM: 4 prompts move into the registry (persona/quality/distribution domains).
- Observability: none (no new Langfuse metadata).
- Deployment: prompt files must be packaged in the image (registry dir already is).

## Dependencies

- Provisional epic id: **RES-5** (Phase 1).
- Gating ADR: governed by the prompt-registry intent in arch-plan §10 (ADR set). No ADR
  must be Accepted to proceed (behavior-preserving).
- Blocked by: **AE-0242 (RES-4)** — delete the dead constant first so the persona
  registry file is sourced unambiguously from the live `_build_style_guide`.
- Blocks: **AE-0252 (RES-13, DeepSeek pilot)** — `QualityAgent` must be on-registry
  before a cheap model is wired to it (arch-plan §9/§13.2).
- Related: **AE-0244 (RES-6)** — the checker that prevents regression once this lands.

## Implementation Plan

1. Author the 4 registry files; for `persona/v1/enforce.yaml` use Jinja2 with the same
   variables `_build_style_guide` consumes (persona name, tone, forbidden phrases,
   writing samples).
2. Add golden-output parity tests (render == legacy f-string) BEFORE switching the call
   sites, capturing the legacy output as the golden fixture.
3. Switch the 4 call sites to `render_prompt`; keep a 1-line fallback constant each.
4. Confirm `quality_agent.py` has zero inline prompts; run gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (registry-unavailable fallback path)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:30

Created from the agent-architecture-restructure epic (RES-5). Scope = the 4 ACTIVE
prompts only; the dead `TEMPLATE_ENFORCE` is handled by AE-0242.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **Golden-output parity mandated.** Moving f-strings to Jinja2 YAML can silently
  change whitespace/ordering and drift model output (arch-plan §12). Parity tests make
  the refactor observably equivalent — without them this is a behavior change
  masquerading as a refactor.
- **persona/v1/enforce.yaml sourced only from the live `_build_style_guide`** — never
  from the dead `TEMPLATE_ENFORCE` (deleted in AE-0242).
- **Sequenced before the DeepSeek pilot** so the quality phase is on-registry before a
  cheap model is wired to it.

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **Refactor — no public/user-visible behavior change.** Output parity is asserted by
  golden tests, so the registry move is observably equivalent. **No `.feature`
  required; golden-parity unit tests suffice.**
- **No static-analysis rule added here** (AE-0244 carries the rule-fires test).
- **Affected gates:** `backend` ruff/mypy/pytest (`scripts/ci/gates.sh backend`).
- Reviewer/QA to sign off on the no-`.feature` classification.

## Blockers

None.

## Final Summary

Pending.
