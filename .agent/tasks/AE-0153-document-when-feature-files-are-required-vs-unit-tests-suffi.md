# AE-0153 — Document when .feature files are required vs unit-tests-suffice

Status: Review
Tier: T1
Priority: Low
Type: Task
Area: Cross-cutting
Owner: developer-skill
Branch: feat/ae-0152-0155-frontend-quality-epic
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

- [x] CLAUDE.md + both AGENTS.md name the two cases explicitly, **with concrete
      examples** of each (so "pure refactor" / "CI-config" can't be stretched to
      smuggle behavior changes past `.feature` coverage).
- [x] The "unit-tests-suffice" path **requires documented evidence in the ticket**:
      (a) an explicit "no public/user-visible behavior change" assertion, (b) the
      gate's seeded-violation test (for CI/config tickets), (c) the affected gates
      listed, and (d) reviewer/QA sign-off on the no-`.feature` classification.
      (Skeptical-review: prevents the policy becoming a loophole.)
- [x] A **tie-break authority** is named for when author and QA disagree on whether
      a ticket is behavior-changing (defaults to "require `.feature` when in doubt").
- [x] `docs/guides/qa-checkpoints.md` references the rule.
- [x] No gate, threshold, or check is loosened (ratchet HOLD/UP) — this only
      removes ambiguity; it never waives required coverage.

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

### 2026-06-16 — Skeptical review resolved

External cold critic (`.agent/reports/AE-0152-0155.skeptical-review.md`) flagged
this as a potential loophole (behavior-changing work mislabeled refactor/config to
skip `.feature`). **Accepted** — ACs now require concrete examples, documented
no-behavior-change evidence + reviewer sign-off for the unit-tests path, and a
named tie-break authority (default: require `.feature` when in doubt).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

PASS (wave QA) — see [AE-0152-0155.qa.md](../reports/AE-0152-0155.qa.md). 15/15 frontend gates green; integrity 0 net-new blockers; all ACs MET; 0 blocker findings.

## Blockers

None.
