# AE-0222 — Make invalid-status error self-documenting and document ticket lifecycle

Status: Intake
Tier: T1
Priority: Low
Type: Quality
Area: Agent Workflow
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18
Source: kaizen session-2026-06-18b (P4, class FC1) — `.agent/reports/kaizen-session-2026-06-18b.plan.md`

## Goal

Make a rejected ticket status self-explanatory and document the status lifecycle,
so authors stop guessing invalid values like `Todo`.

## Problem

`scripts/agent_tasks/schema.py` rejects an unknown status with
`f"Invalid status: {new_status}"` (two call sites) — it does **not** list the valid
options. The valid entry state `Intake` (and the fact that `Ready` is T0-only) is
**undocumented** in `CLAUDE.md` or `docs/plans/agentic-delivery-system.md`. In the
AE-0216 session an author set `Status: Todo`, was rejected with no hint, and had to
read `constants.py` to discover `Intake`.

## Scope

- `scripts/agent_tasks/schema.py` — both `Invalid status:` messages list
  `ALL_STATUSES` and note the entry state, e.g.
  `f"Invalid status: {x}. Valid: {', '.join(ALL_STATUSES)}. New tickets enter at 'Intake' ('Ready' is T0-only)."`
- `docs/plans/agentic-delivery-system.md` — add the status lifecycle line
  (Intake → … → Done; `Ready` is T0-only).

## Non-Goals

- Do not refactor unrelated code
- Do not change the set of valid statuses or any transition rule.

## Acceptance Criteria

- [ ] Both `Invalid status:` messages in `schema.py` include the full valid set
      and the `Intake` entry-state note.
- [ ] `docs/plans/agentic-delivery-system.md` documents the status lifecycle.
- [ ] **Unit test**: assert the invalid-status error string contains the valid
      options (and `Intake`) — proves the hint is present, not just absent-of-crash.
- [ ] `validate_all_tickets.py` still passes on the existing tree; mypy + ruff clean.

## Classification (AE-0153 / AE-0180)

Tooling + docs change with no application behavior change (AE-0153: no `.feature`).
Not a static-analysis rule, so AE-0180's seeded-rule test does not strictly apply;
the unit test above nonetheless asserts the improved error fires with the options.

## Repro Steps

1. Set `Status: Todo` on a ticket; run `validate_ticket.py AE-####`.
2. Observe `Invalid status: Todo` with no list of valid values.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-06-18

Ticket created from kaizen session-2026-06-18b (P4).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.

## References

- Kaizen plan: `.agent/reports/kaizen-session-2026-06-18b.plan.md` (P4)
- Code: `scripts/agent_tasks/schema.py` (`Invalid status:`), `constants.py` (`STATUS_*`)
