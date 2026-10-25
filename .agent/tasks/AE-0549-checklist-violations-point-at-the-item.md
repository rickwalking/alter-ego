# AE-0549 — Checklist rule violations point at the item; truncation covers item bodies

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Backend
Owner: QB
Branch: fix/ae-0549-summary-points-field
Created: 2026-10-25
Updated: 2026-10-25

## Goal

The owner sees a checklist violation under the item that needs the fix, and a checklist item cut off mid-sentence is
caught by the gate.

## Problem

`summary_points_missing` (and `closing_actions_missing`) were reported with `field: "body"`:
`content_rule_violations` pinned every structure code to the slide body (`_violation(command, code, _FIELD_BODY)`),
so the editor showed the error under the slide body, not under the checklist item, and Pedro could not find it. The
frontend already routes `summary_points[i].*` paths to the item (`slide-field-errors.ts`). Separately,
`copy_truncated` only checked the slide body, so cut-off item bodies passed (prod carousel 5344: "… reserva mesa por
telefone. Não é", "… an employee has").

## Scope

- `summary_points_missing` names the first incomplete point (`summary_points[i].title` or `summary_points[i].body`),
  or `summary_points` when every point is complete but there are fewer than 3; `closing_actions_missing` does the same
  over `actions` then `features`. `body_empty` keeps `body`.
- `copy_truncated` also checks every checklist item body (`features`, `summary_points`, `actions`), with a rule
  suited to fragments: an open ending (ellipsis, dangling `,:;-`), a dangling connector as the last word, or a body
  written as sentences whose last one has no closing punctuation. A bare fragment ("Revisão automática de PRs") passes.

## Non-Goals

- Frontend changes (the item routing already exists).
- Changing the slide-body truncation rule.

## Acceptance Criteria

- [x] AC1 A summary slide whose second point has no body reports `summary_points_missing` on `summary_points[1].body`.
- [x] AC2 Two complete points (or none) report it on `summary_points`.
- [x] AC3 A closing slide whose first action has no title reports `closing_actions_missing` on `actions[0].title`.
- [x] AC4 An item body ending "… telefone. Não é", on a dangling connector, an ellipsis or a colon is `copy_truncated`
  on that item; short fragments without a full stop are not.
- [x] AC5 The tests fail on the old rules (seeded: 7 failed against `origin/main`).

## Repro Steps

1. Open a summary slide with an incomplete checklist item in the content review.
2. Before: the error shows under the slide body. After: under the item.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-25 01:00

Ticket created from Pedro's report; fix and tests written. The AE-0430 prod fixture (carousel 5344) now also flags the
4 cut-off summary item bodies of slide 2; its expected sets and fake answers are extended (see the dev summary).

## Files Touched

- `backend/src/rag_backend/application/services/carousel/presentation_content_rules.py`
- `backend/src/rag_backend/application/services/carousel/presentation_copy_rules.py`
- `backend/src/rag_backend/application/services/carousel/copy_hygiene_text.py`
- `backend/tests/unit/application/test_slide_item_rule_fields_ae0549.py`
- `backend/tests/features/slide_item_rule_fields_ae0549.feature`
- `backend/tests/unit/application/content_gate_repair_fixtures_ae0430.py`,
  `test_content_gate_repair_ae0430.py`, `test_content_gate_repair_flow_ae0430.py`

## Test Evidence

See `.agent/reports/AE-0549.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
