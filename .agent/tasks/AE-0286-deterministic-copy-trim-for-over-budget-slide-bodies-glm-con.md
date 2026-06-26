# AE-0286 — deterministic copy trim for over-budget slide bodies (glm content viability)

Status: Intake
Tier: T2
Priority: P2
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-25
Updated: 2026-06-25

## Goal

Make the deterministic presentation repair trim over-budget slide bodies to the
per-slide-type character budget and strip a heading repeated in the body, so the
content phase can pass validation even when the chat model (e.g. GLM 5.2) ignores
the copy budgets. The trim is meaning-preserving (sentence-first), never nonsense.

## Problem

GLM 5.2 (a reasoning model) over-writes slide copy 3-4x past the budgets and
restates the heading in the body. The existing `deterministic_repair_slide_payload`
only fixed emoji/dash/sentence-case, so `body_too_long` and
`heading_repeated_in_body` survived every repair and the content phase could never
be approved (verified live: 3 GLM passes returned 552 -> 978 -> 827 char bodies).
This blocks AE-0285 (GLM provider) from producing a publishable carousel.

## Scope

- `presentation_copy_repair.py`: add `_trim_body_to_budget` (sentence-first,
  word-boundary fallback with ellipsis, markup-balancing, never exceeds budget),
  `_strip_heading_from_body`, and a public `repair_body_length_and_heading(payload,
  violations, policy)` (<=3 args). Reuses the validator's own
  `body_budget_for_slide_type` so the trim provably clears the same check.
- `presentation_review_repair.py`: the bounded-repair closure now runs the
  markup repair then the length/heading repair (policy bound from the call site).
- Unit tests incl. the strongest one: repaired payload re-validates with no
  body-too-long / heading-repeat violation. `.feature` added.

## Non-Goals

- No heading-length trim (headings were within budget; out of scope).
- No change to the budgets or the validator.
- Not a substitute for prompt tuning; this is the deterministic safety net.

## Acceptance Criteria

- [ ] `repair_body_length_and_heading` trims an over-budget body to <= budget,
      keeping whole sentences where possible and never cutting mid-word.
- [ ] A heading repeated in the body is removed.
- [ ] Re-validating a repaired (over-budget + heading-repeat) content slide
      reports neither `body_too_long` nor `heading_repeated_in_body`.
- [ ] The repair runs automatically in the content/presentation review flow.
- [ ] `bash scripts/ci/gates.sh backend` green; validated end-to-end by a GLM
      carousel reaching publish.

## Gherkin Scenarios

See `backend/tests/features/glm_content_budget_trim.feature`.

## Affected Areas

- Backend: presentation copy repair + bounded-repair wiring
- Tests: unit tests + .feature
- Frontend: none | API: none | Deployment: none (auto-applies in repair flow)

## Dependencies

- Related: AE-0285 (GLM provider — this makes GLM content publishable).

## Implementation Plan

1. Add trim + heading-strip + `repair_body_length_and_heading` (policy-aware).
2. Wire it after the markup repair in the bounded-repair closure.
3. Unit tests (trim, strip, validator-clears) + .feature.
4. Rebuild backend; finish the GLM carousel through validation -> publish.

## Progress Log

### 2026-06-25 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
