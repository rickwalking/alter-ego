# AE-0452 — Gardener pass 2: real defects (data exposure, async, error handling, frontend effects)

Status: In Development
Tier: T2
Priority: High
Type: Bugfix
Area: Cross-cutting
Owner: Claude (gardener worker)
Agent Lane: developer → qa → release
Branch: fix/ae-0452-<class> (one PR per finding class, base main)
Kanban Card: TBD
Created: 2026-10-21
Updated: 2026-10-21

## Goal

Find real behaviour defects (not style) left after the AE-0446 static pass and
fix each finding class in its own PR, each with a failing test first.

## Problem

AE-0446 ratcheted the static gates (strict tsc/ESLint, pytest warnings as
errors, dead code, comment policy). Defects that the linters cannot see remain:
public surfaces returning private data, unhandled async failures, effects
without cleanup, error details reaching clients, plus the AE-0446 follow-ups
(unreachable step-history drafts branch, unreachable `/chat` middleware branch,
`conversation_service` leftovers, stale docs).

## Scope

- Data exposure on public surfaces (carousels, media, feeds).
- Async: un-awaited work, fire-and-forget failures, timeouts, lock_version paths.
- Error handling: swallowed errors, wrong status codes, leaked exception text.
- Frontend: effect cleanup, unhandled promise rejections, hard-coded strings.
- AE-0446 follow-ups listed above.

## Non-Goals

- Homepage "Latest Posts" (AE-0449), workflow page scroll (AE-0450), chat (AE-0451).
- Mutation testing locally (CI only).

## Acceptance Criteria

- [ ] Public carousel feed: anonymous and non-admin `public=true` lists return only
      finished carousels and no owner-only fields (#179).
- [ ] Each further finding class ships its own PR with a failing-first test.
- [ ] Every PR's CI is fully green; mutation read from the PR-head CI job.

## Gherkin Scenarios

```gherkin
Feature: The public carousel feed hides unfinished carousels and private fields

  Scenario: An anonymous feed never lists an unfinished carousel
    Given a public carousel that is still generating
    When an anonymous visitor lists carousels without a status filter
    Then the generating carousel is not in the list

  Scenario: An anonymous feed item carries no private fields
    Given a public completed carousel with a blog draft, an error message and an output directory
    When an anonymous visitor lists public carousels
    Then its blog markdown, caption, LinkedIn copy, error message, output directory and PDF paths are empty
```

Full file: `backend/tests/features/public_carousel_list_redaction_ae0452.feature`.

## Delta

### ADDED

- `backend/src/rag_backend/api/routes/carousels/public_feed.py` (public feed projection).

### MODIFIED

- `backend/src/rag_backend/api/routes/carousels/crud.py` (`list_carousels`).

### REMOVED

- None.

## Affected Areas

- Backend: carousel list route.
- Frontend: none (the gallery already asks for `status=completed`, and its card
  reads titles, language, slides and design images only).
- Database: none.
- API: `GET /api/carousels` for anonymous / non-admin `public=true` callers.
- Tests: integration tests for the feed.
- Docs: this ticket.
- Prompts/LLM: none.
- Observability: none.
- Deployment: none.

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0446, AE-0444, AE-0449

## Implementation Plan

1. Broad read-only scans (backend async, public exposure + errors, frontend
   effects/i18n, AE-0446 follow-ups); verify every hit by reading the code.
2. One PR per confirmed class, failing test first.

## Findings

| Class | Finding | Status |
| --- | --- | --- |
| Data exposure | `GET /api/carousels` (anonymous, or non-admin `public=true`) returned the full project: `blog_markdown` (the body of blog posts that are now hidden drafts), caption, LinkedIn copy, POV brief, persona/hook ids, `error_message`, `output_dir`, PDF paths, research sources; it also listed public carousels that are still generating or failed, which the public viewer 404s | #179 |
| Frontend effect cleanup | Workflow polling fallback kept polling `workflow/state` after the workspace unmounted (late poll answer re-armed the timer; no cleanup without `EventSource`) | #182 |
| Public SEO surface | `sitemap.xml` on `your-domain.com` with `/chat` + `/dashboard/knowledge` and no content; `robots.txt` and carousel OG images on `alterego.app` (`SITE_URL` default) | #183 |
| Swallowed async failures | Notification mark-as-read, key-point extraction and persona/rubric create rejected into `void` click handlers (no UI feedback); `useResourceCollection.refetch` never cleared a stale error | #184 |
| Rubric threshold input (#212 review) | The legacy >1.0 normaliser sat on the shared input `RubricCriterion`, so create/update rescaled out-of-range thresholds (1.5 → 0.015, 70 → 0.7) instead of a 422; legacy reads divided by 100 for every scale (1-10 stored 7 → 0.07); the board showed "≥ 0.7 (0-100)". Now: strict input (422 above 1.0), normalisation on read only and on the criterion's own scale, board shows "≥ 70% (0-100)" | this PR |

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-21 23:50

Scans done; public carousel list fix in its own PR.

## Files Touched

See each PR.

## Test Evidence

See each PR.

## QA Report

Pending.

## Decision Log

- An admin keeps the full project on every list (the dashboard needs it); the
  redaction applies to the public feed view only.
- The public feed view (anonymous, or non-admin `public=true`) is always served
  `status=completed`, the same rule as the public viewer
  (`assert_carousel_public_completed`); slides are dropped from its items
  (their `image_path` is a server path).

## Blockers

None.

## Final Summary

Pending.
