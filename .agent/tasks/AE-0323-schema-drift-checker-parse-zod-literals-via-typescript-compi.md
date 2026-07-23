# AE-0323 — schema-drift checker: parse zod literals via typescript compiler api to kill comment false positives

Status: In Development
Tier: T1
Priority: Medium
Type: Quality
Area: frontend
Owner: Unassigned
Branch: TBD
Created: 2026-07-22
Updated: 2026-07-22

## Goal

`check-schema-drift.mjs` extracts Zod object-literal fields via the TypeScript
compiler API so comments and string contents can never corrupt field extraction —
without weakening genuine drift detection.

## Problem

Kaizen failure class FC-3 (`.agent/reports/kaizen-session-2026-07-22.signal.md`).
`splitTopLevelFields()` in `frontend/scripts/check-schema-drift.mjs` char-walks
the raw literal body with no comment or string awareness (verified 2026-07-22).
Incident (learnings-log 2026-07-01, PR #80 wave): an inline `// AE-0298` comment
inside a mapped Zod literal was reported as field `// AE-0298` →
EXTRA-FRONTEND-FIELD gate failure; the "fix" was deleting legitimate comments and
promoting a permanent landmine ("inline comments break the Zod schema-drift
parser"). A gate steering code style via a parser bug erodes trust in all gates.

## Scope

- Replace the hand-rolled field walker with TypeScript compiler API extraction of
  object-literal property names/values (`typescript ^5` is already a direct
  frontend dependency — no new dep).
- Keep the existing coarse type normalization (string/number/boolean/array/
  object/OPAQUE) and all downstream drift comparisons unchanged.
- Remove the now-obsolete inline-comment landmine from docs after merge.

## Non-Goals

- No change to what counts as drift (detection surface must be preserved).
- No new dependencies.
- Do not refactor unrelated code.

## Acceptance Criteria

- [ ] Seeded literal WITH inline `//` and `/* */` comments parses to the correct
      field set (regression test for the AE-0298 incident).
- [ ] Seeded genuine drift (extra frontend field, missing required API field,
      type mismatch) still FAILS the gate — AE-0180 rule-fires tests.
- [ ] False-negative guards: fields whose values contain template literals, regex
      literals, strings containing `//` or `,`/`{`, and nested quoted keys are all
      extracted correctly (cold-critic WARN-3: prove no new false negatives).
- [ ] Gate passes on the current real tree (no behaviour change on clean input).

## Repro Steps

1. Add `// any comment` inside a Zod object literal mapped in
   `check-schema-drift.mjs` entries (e.g. in `carousel.ts`).
2. Run the frontend schema-drift gate → today: comment reported as an
   EXTRA-FRONTEND-FIELD. False positive.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Decision Log

- Cold-critic WARN-3 (2026-07-22): a naive comment-stripper risks trading false
  positives for silent false negatives. Resolved: use the TS compiler API instead
  of hardening the hand-rolled walker; ratchet is UP conditional on the
  false-negative test set.

## Progress Log

### 2026-07-22

Ticket created by kaizen session-2026-07-22 (proposal P3). Plan:
`.agent/reports/kaizen-session-2026-07-22.plan.md`.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
