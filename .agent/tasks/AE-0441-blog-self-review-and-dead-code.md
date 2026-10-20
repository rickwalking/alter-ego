# AE-0441 — Remove the blog "a different editor must review" rule + knip dead-code cleanup

Status: In Progress
Tier: T1
Priority: P1
Type: Bug
Area: Backend, Frontend
Owner: Claude (owner request via orchestrator, 2026-10-20)
Agent Lane: developer → qa → release
Branch: feat/ae-0441-blog-self-review-dead-code
Kanban Card: TBD
Created: 2026-10-20
Updated: 2026-10-20

## Goal

The single author can submit, approve and publish their own blog post on prod, and the
frontend carries no dead code that knip can prove unused.

## Problem

Prod has ONE user (admin). Blog flow: draft → submit-review → approve → publish (publish
requires `approved`, `blog_post_workflow.py:345`). `_resolve_reviewer`
(`blog_post_workflow.py:139-155`) rejected reviewer == author with `self_review_not_allowed`
unless `BLOG_ALLOW_SELF_REVIEW=true`, and the deploy never writes that variable
(`deploy.yml` rewrites the whole `.env` from a fixed list). Result: no blog post can be
published on prod. ADR-0025 and the architecture doc already said the single-author flow
needs self-review. The owner decided to **remove** the rule, not flip the flag.

## Scope

1. Blog only: the author may review/approve/publish their own post. `submit-review` with no
   reviewer → the current post's author is the reviewer; reviewer == author is allowed.
   - Delete `BLOG_ALLOW_SELF_REVIEW` (`settings.py`, `backend/.env.example`).
   - Delete `GET /blog-editor/settings` + `BlogEditorSettingsResponse` (it only carried
     `allow_self_review`) and the frontend code reading it; the editor always behaves as
     "self review allowed" ("Publish now" on a draft, reviewer field optional).
   - Keep every other guard (status transitions, `assert_ready_to_publish`, reviewer must be
     a valid editor user, row locks).
   - Carousel editorial self-review check (`carousels/editorial_workflow.py:~181`) untouched,
     so `ERR_SELF_REVIEW` stays.
2. Specs/tests: AE-0424 Gherkin (backend + frontend) and AE-0438 Gherkin rewritten to the new
   rule; `test_blog_review_flow_ae0424.py` covers submit → approve → publish by the same
   single user end to end; `openapi.json` regenerated; ADR-0025 / architecture doc updated.
3. knip (frontend) + backend dead-code gate: remove what is really dead.

### Decisions

- `assign_content_reviewer` (`resource_access.py`, used only by
  `POST /notifications/assign-review`, which only supports blog posts) also rejected the
  author with `ERR_SELF_REVIEW`. That is the same blog rule on a second door, so it is removed
  too; otherwise the single owner still could not assign themselves in the review panel.
- With no blog path producing `self_review_not_allowed`, the frontend editor-error mapping for
  it (AE-0438) and its `errors.code.self_review` copy are removed; the carousel UI never used
  that blog-editor map.
- The draft "Publish" button (status-guard error, AE-0438 F-11) is kept as is.

## Non-Goals

- Carousel editorial workflow review rules.
- Unused npm dependencies / other knip categories beyond files + exports (listed as a
  follow-up below if any remain).

## Acceptance Criteria

- [ ] AC1: the author can submit their own post with no reviewer (author assigned) or with
  their own id, approve it and publish it; a distinct reviewer still works.
- [ ] AC2: `BLOG_ALLOW_SELF_REVIEW`, `GET /blog-editor/settings` and the frontend settings
  query are gone; the editor always offers "Publish now" on a draft.
- [ ] AC3: other guards still hold (draft cannot publish, invalid reviewer rejected,
  unpublishable draft cannot be submitted, row locks).
- [ ] AC4: Gherkin updated first; tests reference the scenarios; openapi regenerated; ADR and
  architecture doc updated.
- [ ] AC5: knip dead files/exports removed (before/after counts in PR body); backend
  dead-code gate green.
- [ ] AC6: backend + frontend gates (except local mutation) green locally; CI green.

## Gherkin Scenarios

- `backend/tests/features/blog_post_ai_contract_ae0424.feature` (review section)
- `frontend/tests/features/blog_editor_ae0424.feature` (self-review scenarios)
- `frontend/tests/features/blog_editor_errors_ae0438.feature`
- `frontend/tests/features/blog_post_editorial.feature`

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-20

Ticket created from the orchestrator brief; rule removal started.

## Files Touched

TBD

## Test Evidence

TBD

## QA Report

Pending.

## Blockers

None.

## Final Summary

TBD
