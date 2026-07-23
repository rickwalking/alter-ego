# AE-0327 — carousel patch slides merges stale checkpoint copy and clobbers repaired slides

Status: In Development
Tier: T2
Priority: High
Type: Bugfix
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-07-22
Updated: 2026-07-22

## Goal

`PATCH /api/carousels/{id}/slides` never regresses slides it was not asked to
change: unsubmitted slides keep their current live (projection) content instead
of being overwritten from the stale parked checkpoint.

## Problem

Prod incident 2026-07-22 on project `ee540af1-d24d-4da6-a751-2fbbdbd7d4b8`
(kaizen supplemental S1). Operational sequence: POST `/repair` fixed
sentence-casing on slides 2, 4, 6, 7 (writing to the DB projection); a
subsequent PATCH `/slides` submitting only a few targeted slides merged the
submitted slides with the **parked CHECKPOINT copy** — which is staler than the
projection — and rewrote ALL slides, silently clobbering the repair's fixes.
Recovery required re-running POST `/repair` after the PATCH. Current operator
rule ("always PATCH first, repair second, or re-repair after") is tribal
knowledge for a data-loss-shaped bug.

## Scope

- Make the PATCH merge base the live projection (or equivalently: only touch the
  slides actually submitted), not the parked checkpoint copy.
- Keep the checkpoint consistent with whatever the endpoint persists (no new
  projection/checkpoint divergence — this is the recurring checkpoint-vs-
  projection staleness class, see also the AE-0292-era approve-gate incident).
- Alternative acceptable design (architect to decide): auto re-run the repair
  pass server-side after the merge, atomically.

## Non-Goals

- No changes to the repair endpoint's own logic.
- No workflow/phase-machine changes beyond the merge-base fix.

## Acceptance Criteria

- [ ] `.feature` scenarios (behavior-changing bugfix, AE-0153): happy path
      (PATCH one slide → only that slide changes), regression path (repair →
      PATCH a different slide → repaired slides keep their repaired content),
      failure/edge (PATCH with stale lock_version → 409/412 per existing
      convention).
- [ ] Regression test reproducing the 2026-07-22 clobber sequence fails on
      current code and passes with the fix.
- [ ] Checkpoint and projection agree on slide content after PATCH (drift
      assertion in the test).
- [ ] Existing PATCH behaviour for fully-submitted slide sets unchanged.

## Repro Steps

1. Run POST `/repair` on a project with casing violations → projection updated.
2. PATCH `/slides` submitting a single different slide.
3. Today: response/DB shows ALL slides rewritten from the stale checkpoint; the
   repaired slides have reverted.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-07-22

Ticket created by kaizen session-2026-07-22 (supplemental S1, user-approved).
Plan: `.agent/reports/kaizen-session-2026-07-22.plan.md`.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
