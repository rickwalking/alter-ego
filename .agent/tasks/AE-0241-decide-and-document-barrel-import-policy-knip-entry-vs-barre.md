# AE-0241 — Decide and document barrel-import policy (knip entry vs barrel imports)

Status: Intake
Tier: T1
Priority: Low
Type: Quality
Area: frontend
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Make an explicit, documented decision about how re-export barrels (`index.ts`) are
used in the frontend, so knip stops flagging them ambiguously and contributors have a
clear import convention to follow.

## Problem

knip flags several barrels as "unused files" because consumers bypass them:
- **Design-system barrels** `src/components/atoms/index.ts` and
  `src/components/molecules/index.ts` — ~128 imports use concrete paths
  (`@/components/atoms/neon-button`), so the barrels are effectively dead.
- **Bounded-context module barrels** (`modules/knowledge/components`,
  `modules/publishing/blog/hooks`, `modules/publishing/distribution/{components,hooks}`)
  — re-exported via parent barrels (AE-0137/AE-0139 pattern); arguably intentional.

This is an architectural convention question, not a deletion: leaving it implicit means
the same ambiguity (and the same knip noise) recurs at every cleanup. The cold-critic
flagged that the two resolutions are **not symmetric** and must be a deliberate,
documented choice.

Reports: `.agent/reports/kaizen-session-2026-06-18c.{signal,plan,skeptical-review}.md`.

## Scope

- A short decision: barrels as public-API contract (consumers import via the barrel) vs
  optional sugar (configure the intentional barrels as knip `entry`).
- Capture it in an ADR (`docs/decisions/`) or the existing frontend module-convention
  doc; reflect it in `knip.json`.

## Non-Goals

- **Do NOT** bulk-migrate the ~128 direct imports without the decision (large,
  review-heavy, no behavioral benefit) — that only happens IF the decision is
  "barrel as public-API contract", and even then can be a separate ticket.
- No file deletions (that is AE-0240).

## Acceptance Criteria

- [ ] A written decision exists (ADR or module-convention doc) stating, for (a)
      design-system barrels and (b) module barrels, whether the barrel is the required
      import surface or optional, and why.
- [ ] `knip.json` reflects the decision: intentional-but-bypassed barrels are
      configured as `entry` (so they are no longer false "unused"), OR a follow-up
      migration ticket is referenced if the team chose barrel-as-contract.
- [ ] After the change, `knip` no longer reports the *intentional* barrels as unused
      (only genuinely-dead files remain — handled by AE-0240).
- [ ] `bash scripts/ci/gates.sh frontend` green.

## Gherkin Scenarios

```gherkin
Feature: Barrel policy is decided and enforced

  Scenario: Intentional barrel configured as entry
    Given the team decides design-system barrels are optional sugar
    When knip.json marks them as entry points
    Then knip no longer reports them as unused
    And the decision is recorded in a doc/ADR
```

## Delta

### ADDED
- An ADR or a section in the frontend module-convention doc.
- `knip.json` `entry`/config updates per the decision.

### MODIFIED
- `frontend/knip.json` (or wherever knip config lives).

### REMOVED
- None.

## Affected Areas

- Frontend: knip config + docs.
- Tests: none (config/doc); `gates.sh frontend` must stay green.
- Deployment: none.
- Docs: ADR / module-convention doc.

## Dependencies

- Blocks: removes recurring knip ambiguity at future cleanups.
- Blocked by: none (independent of AE-0240).
- Related: AE-0240 (dead-file deletion), AE-0137/AE-0139 (module barrel pattern), AE-0178.

## Implementation Plan

1. Decide: barrel-as-contract vs optional-sugar, separately for design-system vs module
   barrels (default recommendation: module barrels = intentional `entry`; design-system
   barrels = decide with the team).
2. Write the ADR/doc; update `knip.json`.
3. Confirm knip no longer flags the intentional barrels; `gates.sh frontend` green.

## Test Classification (CLAUDE.md AE-0153)

- **Config/doc ticket — no public/user-visible behavior change.** **No `.feature`
  required**; the proof is "knip no longer flags the intentional barrels" + green gate.
- **Affected gates:** knip dead-file advisory + `gates.sh frontend`.
- Reviewer/QA to sign off on the no-`.feature` classification.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:00

Created by kaizen session-2026-06-18c. Split out from AE-0240 per the cold-critic
(opencode): the barrel convention is an architectural decision that must be documented,
not buried in a deletion ticket.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **Critic [INFO] barrel policy is asymmetric & lasting** — ACCEPTED: this ticket exists
  precisely to make the choice explicit and documented (ADR/doc), and to avoid a
  blind 128-import migration. Default lean: configure intentional barrels as knip
  `entry`; revisit barrel-as-contract only with team alignment.

## Blockers

None.

## Final Summary

Pending.
