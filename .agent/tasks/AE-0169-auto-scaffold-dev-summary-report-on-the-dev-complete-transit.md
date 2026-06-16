# AE-0169 — Auto-scaffold dev-summary report on the Dev Complete transition

Status: Intake
Tier: T1
Priority: Medium
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Branch: TBD
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

- [ ] Moving a ticket to Dev Complete creates `.agent/reports/<id>.dev-summary.md` (template) when missing; existing files are never overwritten.
- [ ] `schema.py` validation rules unchanged; `validate_all_tickets.py` still enforces presence.
- [ ] Verified: a fresh ticket → Dev Complete produces a valid dev-summary skeleton and passes validation.

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

Pending.

## QA Report

Pending.

## Blockers

None.
