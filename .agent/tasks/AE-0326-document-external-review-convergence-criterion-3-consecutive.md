# AE-0326 — document external-review convergence criterion: 3 consecutive zero-blocker rounds default stop rule

Status: In Development
Tier: T1
Priority: Low
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Branch: TBD
Created: 2026-07-22
Updated: 2026-07-22

## Goal

The external cold-critic/QA loop has a documented default stop rule — 3
consecutive zero-BLOCKER rounds — so sessions stop re-deriving it and neither
polish forever nor stop prematurely.

## Problem

Kaizen failure class FC-6 (`.agent/reports/kaizen-session-2026-07-22.signal.md`).
The cold-critic system prompt (`skills/delivery/architect-skill/prompts/
cold-critic-system.md`) MANDATES ≥3 material findings per round, so a literal
zero-findings verdict is structurally unreachable. Two sessions independently
re-derived the same trajectory-based stop rule (security-tickets loop stopped at
rounds 7–9 with three consecutive zero-blocker rounds; the AE-0295..0299 loop
used the same logic over 5 rounds). Verified 2026-07-22: not documented anywhere
in architect-skill or kaizen-skill references.

## Scope

- Add a "Convergence" section to the architect-skill skeptical-mode reference and
  the kaizen external runbook: converged = **3 consecutive rounds with zero
  BLOCKERs** (track severity trajectory, not verdict text), as the DEFAULT stop
  rule — overridable in either direction with a recorded justification in the
  review record.
- Calibration caveat: BLOCKER/WARN boundary drift across reviewer models is a
  known noise source; n=2 sessions is the current empirical basis — revisit if a
  converged wave later ships a blocker-class defect.
- Explicitly state the down-ratchet guard: never weaken the ≥3-findings mandate
  to make literal-zero reachable.
- Ride-along one-liner in the same runbook: prettier is non-idempotent on inline
  code spans wrapped across line breaks in `.md` list items (rejoin the span).

## Non-Goals

- No changes to the cold-critic prompt itself.
- No new gates or scripts — documentation only.

## Acceptance Criteria

- [ ] Convergence section present in both skill references with the default rule,
      override-with-justification clause, and calibration caveat.
- [ ] Down-ratchet guard sentence present (≥3-findings mandate must not be
      weakened).
- [ ] Prettier non-idempotence landmine documented.
- [ ] AE-0153 no-`.feature` classification recorded (docs-only, no behavior
      change; no seeded-violation test applicable — no rule/gate added).

## Repro Steps

1. Run any multi-round external cold-critic loop.
2. Today: the reviewer can never return zero findings, and the stop rule exists
   only in session memory/handoffs.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Decision Log

- Cold-critic WARN-6 (2026-07-22): don't canonize an n=2 heuristic as absolute.
  Resolved: documented as default-not-absolute with recorded-justification
  override and severity-calibration caveat.

## Progress Log

### 2026-07-22

Ticket created by kaizen session-2026-07-22 (proposal P6). Plan:
`.agent/reports/kaizen-session-2026-07-22.plan.md`.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
