# AE-0153 — Document when .feature files are required vs unit-tests-suffice

Status: Intake
Tier: T1
Priority: Low
Type: Task
Area: Cross-cutting
Owner: Unassigned
Branch: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Clarify the "Gherkin-first" testing standard so it states when a `.feature` file
is required versus when focused unit tests suffice — removing a recurring,
non-actionable QA warning.

## Problem

Source: kaizen `.agent/reports/kaizen-AE-0149-0151.plan.md` (failure class #2).
CLAUDE.md mandates a "Gherkin-first approach" but is silent on pure-refactor and
CI/config tickets. AE-0150 (refactor) and AE-0151 (CI-config) shipped with no
`.feature` file — fully covered by unit tests + the gate's own seeded-violation
test — yet QA flags "missing .feature" on every such ticket. The standard needs
an explicit scope so the signal is actionable, without loosening any gate.

## Scope

- `CLAUDE.md` (Testing) + `frontend/AGENTS.md` + `backend/AGENTS.md`: state two
  cases — behavior-changing feature/bugfix tickets require `.feature` scenarios
  (happy + edge + failure); pure refactors and CI/config tickets may substitute
  focused unit tests + the gate's seeded-violation test, cited in the ticket.
- `docs/guides/qa-checkpoints.md`: reference the clarified rule so QA applies it.

## Non-Goals

- Do not refactor unrelated code
- Loosening any gate or coverage threshold (documentation/scoping change only).

## Acceptance Criteria

- [ ] CLAUDE.md + both AGENTS.md name the two cases explicitly.
- [ ] `docs/guides/qa-checkpoints.md` references the rule.
- [ ] No gate, threshold, or check is loosened (ratchet HOLD/UP).

## Repro Steps

1. Review the AE-0150 / AE-0151 QA report: "missing .feature" raised despite full
   unit-test coverage — a non-actionable warning under the current wording.

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
