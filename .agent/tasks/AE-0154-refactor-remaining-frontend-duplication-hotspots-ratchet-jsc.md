# AE-0154 — Refactor remaining frontend duplication hotspots + ratchet jscpd toward ~1%

Status: Intake
Tier: T2
Priority: Medium
Type: Refactor
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Pay down the remaining frontend source-duplication clones (the hotspots AE-0150
left as out-of-scope) so the jscpd `threshold` in `frontend/.jscpd.json` can
ratchet further DOWN, toward ~1%.

## Problem

AE-0150 de-duped the top 3 named hotspots (SSE hooks, carousel routes,
api-client), dropping source duplication 1.45% → **1.08%** and ratcheting the
jscpd threshold 2 → 1.2. Per AE-0150's non-goal ("do not over-DRY; readability
wins"), the remaining clones were intentionally left. They are now the next
tranche of debt. Current `npx jscpd src`: **26 clones, 1.08% (350 dup lines)**.

Remaining clones (from `frontend/reports/jscpd/jscpd-report.json`):
- `create-theme-section.tsx` ~ `create-topic-section.tsx` ~ `create-template-section.tsx`
  (27L/20L/19L — the dashboard "create workspace" section components share structure).
- `app/dashboard/personas/page.tsx` ~ `app/dashboard/rubrics/page.tsx` (24L — list-page scaffold).
- `components/admin/create-user-dialog.tsx` ~ `edit-user-dialog.tsx` (17L + 16L — user dialog form).
- `app/dashboard/chat/error.tsx` ~ `knowledge/error.tsx` (18L — route error boundary).
- `modules/.../use-editorial-workflow-utils.ts` self-clone (27L).
- `accessibility-checker.tsx` ~ `seo-preview.tsx` (15L); `login/page.tsx` ~ `public-header.tsx`
  ~ `neon-sidebar.tsx` (15L/14L); `blog-post-admin-panel.tsx` self-clone (13L).

## Scope

- Refactor the clones above into shared components/hooks/utils **where it
  genuinely improves clarity** (e.g. a shared create-workspace section primitive,
  a shared list-page scaffold, a shared user-dialog form, a shared route-error
  boundary).
- Lower the jscpd `threshold` in `frontend/.jscpd.json` to the new measured level
  (ratchet DOWN, toward ~1%).

## Non-Goals

- Over-DRYing: do not couple unrelated code just to cut clones (readability wins).
- Test-file duplication (advisory only — AE-0151).

## Acceptance Criteria

- [ ] **Per-clone semantic justification BEFORE extracting** — each targeted clone
      is classified as *semantically shared* (one concept that should evolve
      together) vs *coincidentally similar* (route error boundaries, list pages,
      create/edit dialogs, marketing markup often differ in intent). Only extract
      the semantically-shared ones. (Skeptical-review: don't couple unrelated code
      to chase a percentage.)
- [ ] **Readable duplication may be explicitly WAIVED**, not force-extracted —
      record a jscpd `ignore`/inline-ignore with a one-line reason for any clone
      kept on purpose; the threshold reflects post-waiver reality. A waiver is a
      legitimate outcome for a clone, not a failure.
- [ ] Server/client boundary preserved — no extraction moves logic across a
      Next.js `"use client"`/server boundary or changes a component's render env.
- [ ] The extracted (semantically-shared) clones are removed (jscpd confirms);
      `npx jscpd src` source duplication drops below the current 1.08% level.
- [ ] jscpd `threshold` lowered to the new measured level (ratchet down) and the
      `frontend:duplication` gate is green.
- [ ] No behavior change (tests pass; all frontend gates green).

## Gherkin Scenarios

```gherkin
Feature: Reduce remaining frontend source duplication

  Scenario: Shared extraction removes a clone and ratchets the threshold
    Given two components duplicated a block of UI/logic
    When the shared primitive is extracted and both use it
    Then jscpd reports the clone resolved, the threshold is lowered, and
      behavior is unchanged
```

## Delta

### ADDED

- ...

### MODIFIED

- ...

### REMOVED

- ...

## Affected Areas

- Backend:
- Frontend:
- Database:
- API:
- Tests:
- Docs:
- Prompts/LLM:
- Observability:
- Deployment:

## Dependencies

- Blocks:
- Blocked by:
- Related: AE-0149 (the gate + ratchet), AE-0150 (first hotspot tranche; this is
  its follow-on). The kaizen-jscpd plan anticipated ratcheting "toward ~1%".
- **Blocks: AE-0152** — this refactor moves exports / creates shared primitives /
  changes barrel behavior; do it first so AE-0152's knip baseline is snapshotted
  on the settled tree (skeptical-review sequencing finding).

## Implementation Plan

1. ...

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-06-16 — Skeptical review (`.agent/reports/AE-0152-0155.skeptical-review.md`,
  external cold critic): **WARN accepted** — guard against metric-chasing/harmful
  coupling: require per-clone semantic justification, allow explicit
  readable-duplication waivers, and preserve server/client boundaries (ACs added).
  **WARN accepted** — sequenced before AE-0152 (this refactor churns knip results).

## Blockers

None.

## Final Summary

Pending.
