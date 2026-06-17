# AE-0174 — Refactor remaining frontend duplication hotspots + ratchet jscpd toward ~1%

Status: Review
Tier: T2
Priority: Medium
Type: Refactor
Area: Frontend
Owner: developer-skill
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0152-0155-frontend-quality-epic
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

> **Result:** source duplication 1.08% → **0.72%** (26 → 18 clones, 350 → 233
> dup lines); jscpd threshold ratcheted 1.2 → **0.8**. All 14 frontend gates PASS;
> integrity clean. Extract/waive decisions in the Decision Log.

- [x] **Per-clone semantic justification BEFORE extracting** — each targeted clone
      is classified as *semantically shared* (one concept that should evolve
      together) vs *coincidentally similar* (route error boundaries, list pages,
      create/edit dialogs, marketing markup often differ in intent). Only extract
      the semantically-shared ones. (Skeptical-review: don't couple unrelated code
      to chase a percentage.)
- [x] **Readable duplication WAIVED** — the remaining 18 clones are intentionally
      accepted under the lowered 0.8 threshold (the threshold IS the waiver
      mechanism for this gate; chose threshold-absorption over scattering 18
      inline-ignore directives across the codebase). Per-clone reasons in the
      Decision Log.
- [x] Server/client boundary preserved — extractions are presentational/schema
      only; `public-chat-view ↔ dashboard-chat-view` was WAIVED specifically to
      avoid touching the server/client boundary (skeptical-review caution).
- [x] The extracted (semantically-shared) clones are removed (jscpd confirms);
      `npx jscpd src` source duplication dropped 1.08% → **0.72%**.
- [x] jscpd `threshold` lowered 1.2 → **0.8** (ratchet down) and the
      `frontend:duplication` gate is green.
- [x] No behavior change: typecheck + eslint clean; new component tests (10) +
      existing suites pass; all 14 frontend gates PASS; integrity clean.

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
- **Blocks: AE-0172** — this refactor moves exports / creates shared primitives /
  changes barrel behavior; do it first so AE-0172's knip baseline is snapshotted
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

PASS (wave QA) — see [AE-0172-0175.qa.md](../reports/AE-0172-0175.qa.md). 15/15 frontend gates green; integrity 0 net-new blockers; all ACs MET; 0 blocker findings.

## Decision Log

- 2026-06-16 — Skeptical review (`.agent/reports/AE-0172-0175.skeptical-review.md`,
  external cold critic): **WARN accepted** — guard against metric-chasing/harmful
  coupling: require per-clone semantic justification, allow explicit
  readable-duplication waivers, and preserve server/client boundaries (ACs added).
  **WARN accepted** — sequenced before AE-0172 (this refactor churns knip results).

- 2026-06-16 — **Extract/waive decisions (per-clone):**

  **EXTRACTED (semantically shared, low risk):**
  - Dashboard route error boundaries (`chat/error.tsx` ~ `knowledge/error.tsx`) →
    `components/molecules/route-error-view.tsx` (`RouteErrorView`). Verified
    identical markup; differ only by namespace / log label / optional message.
  - Status badges (`personas/status-badge` ~ `rubrics/rubric-status-badge`) →
    `components/atoms/status-pill.tsx` (`StatusPill`). Differ only by colour palette.
  - create-carousel sections (`create-{topic,theme,template}-section`) → shared
    `section-styles.ts` (card/header/input styles) + `labeled-field.tsx`
    (`LabeledField`). Pure presentational; byte-identical styles.
  - Schemas: `documentUploadResponseSchema = documentSchema` (knowledge.ts);
    `carouselBlogWithDesignResponseSchema = carouselBlogI18nResponseSchema.extend(...)`
    (carousel.ts). Same inferred types — zero risk.
  - New shared pieces covered by unit tests (StatusPill, LabeledField, RouteErrorView).

  **WAIVED (accepted under the 0.8 threshold; extraction would over-couple or is
  too risky for the reward):**
  - Admin dialogs (`create-user` ~ `edit-user` ~ `change-password`) — stateful
    forms with **no tests**; the skeptical review explicitly flagged "admin
    create/edit dialogs" as verify-don't-assume. Shared Tailwind field/footer
    markup is acceptable readable duplication; revisit only with test coverage.
  - List pages (`personas` ~ `rubrics` ~ `blog-posts/page`) — page-level layout
    scaffolds; coincidental structure, distinct data/actions.
  - `public-chat-view` ~ `dashboard-chat-view` — server/client boundary risk
    (skeptical-review caution) > reward.
  - Nav/marketing markup (`login/page` ~ `public-header` ~ `neon-sidebar`),
    blog tools (`accessibility-checker` ~ `seo-preview`), editorial panels
    (`review-assignment-panel` ~ `scheduled-publish-picker`) — coincidental
    similarity, not one evolving concept.
  - Small self/hook clones (`use-editorial-workflow-utils`, `use-documents` ~
    `use-upload`, `use-collaborative-edit`, `dashboard/page`,
    `blog-post-admin-panel`, 8-line icon/preview clones) — indirection cost
    exceeds the benefit at this size.

## Blockers

None.

## Final Summary

Pending.
