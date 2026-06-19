# AE-0254 — close anti-hardcoded-prompt checker blind spot (marker-allowlist evasion)

Status: Intake
Tier: T2
Priority: Medium
Type: Quality
Area: backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-19
Updated: 2026-06-19

## Goal

Make `scripts/check_inline_prompts.py` (AE-0244) catch the inline-prompt class it
currently misses — short, marker-less, generically-named inline prompts — so the gate,
not downstream human/external QA, is the backstop against reintroducing hardcoded prompts.

## Problem

`check_inline_prompts.py:53` (`_looks_like_prompt`) flags a string only if it contains a
newline AND one of **6 hardcoded marker phrases** (`PROMPT_MARKERS`, lines 42-49). The
real `evaluate_eeat` prompt contained **none** of them, so the gate missed it; it was
caught only by external QA. The remediation (AE-0244 follow-up) appended `"Format as JSON"`
to both the prompt and the marker list — whack-a-mole. The pre-migration prompt (now
`agents/prompts/quality/v1/eeat.yaml`) was ~4 lines, marker-less, assigned to a generic
local `prompt` — it evades a marker allowlist, a line-count threshold, AND a `*_PROMPT`-name
check alike. A future inline prompt with the same shape is missed identically; the gate is
gameable by simply not self-identifying the prompt.

Source: `.agent/reports/kaizen-session-2026-06-19.plan.md` (failure class #1) +
`.skeptical-review.md` (BLOCK; both P1 blockers accepted and incorporated below).

## Scope

- `scripts/check_inline_prompts.py` — strengthen detection beyond the marker allowlist.
- A rule-fires regression test seeding an `evaluate_eeat`-shaped fixture (AE-0180 standard).
- `docs/guides/qa-checkpoints.md` — note the strengthened rule.

## Non-Goals

- No production-code behavior change (this is a static-analysis/CI rule; **explicit
  "no public/user-visible behavior change" assertion** per CLAUDE.md AE-0153 — unit +
  seeded-violation tests substitute for a `.feature`).
- Not a rewrite to a non-stdlib tool unless the implementer justifies it; keep `ast`-based
  if a sound intra-procedural design suffices.

## Acceptance Criteria

- [ ] **Survey first:** enumerate the LLM-invocation patterns in the scanned dirs
      (`.ainvoke`/`.invoke`, `SystemMessage`/`HumanMessage`, `ChatPromptTemplate.from_*`,
      `self.llm.*` attribute chains, `render_prompt` aliases/re-exports) and record the count
      of each in the ticket before implementing — the detector design depends on this distribution.
- [ ] The checker FIRES (non-zero exit) on **≥3 seeded fixtures** covering the dominant
      patterns: (a) the `evaluate_eeat` class — short (~4-line), marker-less f-string assigned
      to a generic `prompt` then `.ainvoke`'d; (b) an inline string in `SystemMessage(content=...)`;
      (c) a helper function that `return`s a bare multi-line string literal. **Rule-fires
      regression test mandatory (AE-0180)** — asserts non-zero exit on each seeded violation.
- [ ] **Resolution order is specified and tested:** when a call-result argument to an LLM call
      cannot be resolved intra-procedurally to `render_prompt()`/a sanctioned constant, the
      checker's behavior is documented and deterministic (default: flag; the current tree's
      such patterns are refactored to the registry OR carry a documented exemption). "No new
      false positives" (below) applies **after** those refactors/exemptions — the ticket must
      not demand both an unspecified mechanism and zero false positives.
- [ ] Exemption-priority chain implemented and tested: `docstring > *_FALLBACK/*_TEMPLATE >
      detection`. Negative test: `_X_FALLBACK_PROMPT` is NOT flagged.
- [ ] **The FALLBACK/TEMPLATE exemption is restricted to module-level constants** (not
      function-local). A test proves a **function-local** `fallback_prompt = "..."` IS flagged
      (closes the local-scope evasion path the critic found in `_allowed_value_ids`).
- [ ] No new false positives on the current tree **after** documented refactors/exemptions
      (`python scripts/check_inline_prompts.py` green); each exemption justified in-script.
- [ ] Script docstring documents the detection strategy, the resolution order, and the known
      residual gaps (no single heuristic is complete — state which patterns are/aren't covered).

## Recommended direction (not mandatory mechanism)

Invert from "does this string look like a prompt" to the **LLM-call boundary**: every
argument to a model invocation (`.ainvoke`/`.invoke`, `SystemMessage`/`HumanMessage`,
`ChatPromptTemplate.from_*`) must originate from `render_prompt()` or a `*_FALLBACK`/
`*_TEMPLATE` constant — checked intra-procedurally (the dominant pattern). Additionally
flag helper functions in the scanned dirs that `return` a bare multi-line string literal.
The critic showed full data-flow analysis is infeasible with stdlib `ast`; the intra-
procedural call-boundary check + return-literal check is the tractable, robust subset.

## Gherkin Scenarios

```gherkin
Feature: anti-hardcoded-prompt checker catches marker-less inline prompts

  Scenario: short marker-less inline prompt fed to an LLM call is flagged
    Given a module under agents/ with a ~4-line f-string containing no marker phrase
      And that string is assigned to a local named "prompt" and passed to llm.ainvoke
    When check_inline_prompts.py runs
    Then it exits non-zero and reports the file and line

  Scenario: sanctioned FALLBACK_PROMPT constant is not flagged
    Given a multi-line string assigned to "_X_FALLBACK_PROMPT"
    When check_inline_prompts.py runs
    Then it exits zero for that string (exemption priority holds)
```

## Affected Areas

- Backend: scripts/check_inline_prompts.py
- Tests: scripts/check_inline_prompts test (rule-fires + FALLBACK negative)
- Docs: docs/guides/qa-checkpoints.md

## Dependencies

- Blocks: —
- Blocked by: —
- Related: AE-0243, AE-0244 (the checker + the original miss); kaizen-session-2026-06-19

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (helper-returned, short, marker-less, FALLBACK_PROMPT)
- [ ] Orphan/unfinished code checked

## Decision Log

### 2026-06-19 — external cold-critic findings (plan-round, accepted)
- BLOCKER "data-flow infeasible / wouldn't catch evaluate_eeat" — accepted; reframed this
  ticket goal-first and recommended the intra-procedural call-boundary inversion.
- BLOCKER "`*_PROMPT` trigger vs `*_FALLBACK_PROMPT` exemption" — accepted; explicit
  priority chain + negative test are acceptance criteria.

### 2026-06-19 — external architect review of the ticket (round 2, accepted)
- BLOCKER "call-boundary AC vs zero-false-positive AC in tension" — accepted; added a
  **resolution-order AC** and a **survey-first AC**; "no new false positives" now applies
  after documented refactors/exemptions.
- WARN "FALLBACK/TEMPLATE exemption gameable at function-local scope" — **verified** in
  `_allowed_value_ids` (walks whole tree); added an AC restricting the exemption to
  module-level + a test that a function-local `fallback_prompt` IS flagged.
- INFO "single fixture insufficient" — accepted; AC now requires ≥3 fixtures (`.ainvoke`,
  `SystemMessage`, helper `return`).

## Blockers

None.

## Final Summary

Pending.
