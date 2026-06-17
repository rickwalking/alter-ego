# AE-0169 — Auto-scaffold dev-summary report on the Dev Complete transition

Status: Done
Tier: T1
Class: B
Priority: Medium
Type: Quality
Area: Cross-cutting
Owner: developer-skill
Branch: chore/phase-8-class-b
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Auto-scaffold the required `.agent/reports/<id>.dev-summary.md` when a ticket transitions to Dev Complete, so the validator's requirement can't be silently missed. Source: kaizen sweep `.agent/reports/kaizen-sweep-2026-06-16.plan.md` P4.

## Problem

`schema.py` requires `<id>.dev-summary.md` for Dev Complete and `<id>.qa.md` for Review, but `move_ticket.py`/`create_ticket.py` never scaffold the report. In Phase 8, 7 tickets were marked Dev Complete with evidence written into the ticket body instead, and `validate_all_tickets.py` failed for all 7 at once — caught late, fixed by hand. The bar is right; the tooling doesn't help meet it.

## Scope

- On the Dev Complete transition in `scripts/agent_tasks/move_ticket.py`, scaffold `.agent/reports/<id>.dev-summary.md` from a template (pre-filled with the ticket id/title + the required sections: Acceptance Criteria Implemented / Tests Run / Deviations / QA Outcome) if absent.
- Leave the validator (`schema.py`) UNCHANGED — this only makes compliance the default, never loosens the requirement.
- Optionally print a reminder to fill the scaffolded file before Review.

## Non-Goals

- Not weakening or removing the dev-summary / qa.md requirement (would loosen — rejected).
- Not auto-generating fake content; scaffold a template the developer fills.

## Acceptance Criteria

- [x] Moving a ticket to Dev Complete creates `.agent/reports/<id>.dev-summary.md` (template) when missing; existing files are never overwritten. Implemented `scaffold_dev_summary()` in `move_ticket.py`, called on the `Dev Complete` transition.
- [x] `schema.py` validation rules unchanged (only `move_ticket.py` touched) — the validator still enforces presence; this only makes compliance the default.
- [x] Verified: unit tests `backend/tests/unit/agent_tasks/test_move_ticket.py` (creates template w/ required sections + ticket id; never overwrites). **Dogfooded:** this ticket's own `AE-0169.dev-summary.md` was scaffolded by `move_ticket.py AE-0169 --status "Dev Complete"`.

## Repro Steps

1. `create_ticket.py` a ticket, implement, `move_ticket.py <id> --status "Dev Complete"`.
2. `validate_all_tickets.py` → previously errored "no dev summary at <id>.dev-summary.md" (the Phase-8 7-ticket failure).

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-06-16 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

`uv run pytest tests/unit/agent_tasks/ -q` (from `backend/`) → 9 passed, 1 skipped,
including the 3 new `test_move_ticket.py` cases (creates template with required
sections + ticket id; never overwrites an existing report; template placeholder
substituted). Dogfood: `move_ticket.py AE-0169 --status "Dev Complete"` scaffolded
`.agent/reports/AE-0169.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.

## Final Summary

move_ticket.py auto-scaffolds the dev-summary on the Dev Complete transition; schema sentinel prevents unfilled scaffolds. Verified in main.
