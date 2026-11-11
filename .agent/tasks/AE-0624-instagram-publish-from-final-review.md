# AE-0624 — Publish to Instagram from the site while the carousel is at final review

Status: In Development
Tier: T2
Priority: High
Type: Feature
Area: Fullstack
Owner: Claude
Branch: feat/instagram-publish-from-final-review
Created: 2026-11-10
Updated: 2026-11-10

## Goal

The publish page offers Instagram "Publicar agora" while a carousel waits for the owner's final review; one click
approves the final review and posts it, as the Telegram "Publicar agora" does.

## Problem

The publish page showed the Instagram button only once the workflow was `approved_for_publish`, and the route refused
anything else (403). Autopilot carousels are approved on Telegram, so the site never offered the button on them; the
owner asked for it on carousels in the final phase (2026-11-10).

## Scope

- Backend: `POST /api/carousels/{id}/publish/instagram` accepts a carousel at `final_review` / `awaiting_human`.
  After every other check passes it runs `SitePublishApproval`: with an autopilot run it moves the run
  `awaiting_owner → publishing` (or `scheduled → publishing`), approves the final review and releases the carousel;
  without a run it approves the final review. The existing manual publish then posts once. A refused approve answers
  409 `final_review_approve_refused` and puts the run back.
- Frontend: `canPublishInstagram` (approved, or final review awaiting the owner) gates the button; a successful
  publish refreshes the workflow state.

## Non-Goals

- Do not refactor unrelated code
- The site publish button keeps its approved-only rule.
- No schedule choice from the site (owner chose "approve + post now").

## Acceptance Criteria

- [x] At final review the publish page shows the Instagram button, not the site publish.
- [x] Publishing at final review approves the final review, then posts with the saved caption.
- [x] An autopilot run awaiting the owner (or scheduled) is published through its own run, once.
- [x] A refused approve answers 409 and posts nothing; the run goes back to awaiting the owner.
- [x] Caption, artifact and public URL checks run before the approve.
- [x] Before final review the route still answers 403.

## Repro Steps

1. Open the publish page of a carousel at final review.
2. No Instagram publish button is offered.

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-11-10 20:00

Owner chose "approve + post now". Implemented backend use case, route change and frontend rule. Backend gates green;
frontend gates green except `frontend:test`, whose duplication-gate test times out (10 s) under local full-suite
load (passes alone, 5/5); CI decides.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/application/site_publish.py` (new)
- `backend/src/rag_backend/modules/autopilot/bootstrap_site_publish.py` (new)
- `backend/src/rag_backend/modules/autopilot/application/owner_approval.py`
- `backend/src/rag_backend/modules/autopilot/bootstrap_webhook.py`
- `backend/src/rag_backend/modules/autopilot/public.py`, `__init__.py`
- `backend/src/rag_backend/api/routes/carousels/publishing.py`
- `backend/src/rag_backend/domain/constants/carousel_workflow.py`
- `docs/architecture/openapi.json`
- `frontend/src/app/dashboard/create/[id]/publish/{publish-readiness,use-publish-page}.ts`, `page.tsx`
- tests and features (backend + frontend, `ae0624`)

## Test Evidence

- Backend: `test_site_publish_ae0624.py` (14), `test_publish_from_final_review_ae0624.py` (4), existing publish API
  tests; autopilot unit suite + publish integration: 1207 passed. Python 3.11 import ok.
- Frontend: publish page + readiness tests 35 passed.

## QA Report

Pending.

## Blockers

None.
