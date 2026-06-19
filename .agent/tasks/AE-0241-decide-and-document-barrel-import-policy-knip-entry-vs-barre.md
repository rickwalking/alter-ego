# AE-0241 — Decide and document barrel-import policy (knip entry vs barrel imports)

Status: Dev Complete
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

- [x] A written decision exists (`frontend/src/modules/README.md` → "Barrel-import
      policy (AE-0241)", pointer added to `frontend/CLAUDE.md`): (a) top-level module
      barrel = required public contract; (b) design-system barrels, module layer
      sub-barrels, and co-located feature barrels = optional sugar (concrete paths are
      the convention), with the rationale (asymmetry, ~128 bypassing imports, no
      barrel-as-contract migration).
- [x] `knip.json` reflects the decision: the optional barrels are configured as
      `entry` (`src/components/{atoms,molecules}/index.ts`, `src/modules/**/index.ts`,
      `src/app/**/index.ts`). Barrel-as-contract migration explicitly deferred (noted
      as a future, separately-scoped option, not done).
- [x] After the change, `knip` no longer reports the *intentional* barrels as unused;
      the only remaining file-scope findings are the live `app/dashboard/personas/*`
      route files (a separate legacy-UI deferral, AE-0240 Non-Goal).
- [x] `bash scripts/ci/gates.sh frontend` reproduced at the wave level (see dev-summary).

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

- `frontend/src/modules/README.md` — new "Barrel-import policy (AE-0241)" section
  (decision + rationale + knip-config explanation).
- `frontend/CLAUDE.md` — barrel-policy bullet in the import-conventions section,
  linking to the README decision.
- `frontend/knip.json` — added `entry` globs for the optional barrels.

## Test Evidence

```
$ npx knip --include files --no-config-hints
# before: 12 unused files (incl. atoms/molecules/module/feature barrels)
# after:   5 unused files — only app/dashboard/personas/* (live route, AE-0240 Non-Goal)
```

Config/doc ticket — no static-analysis *rule* added (knip `entry` config only), so
no rule-fires test required; the proof is "knip no longer flags the intentional
barrels" + green frontend gates (wave-level).

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
