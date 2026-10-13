# AE-0357 — Idempotent InstagramPublishJob + persisted ig_post_id + publish status route

Status: Ready
Tier: T2
Priority: Critical
Type: Feature
Area: backend
Owner: Grok (Cursor CLI, grok-4.7-high)
Agent Lane: developer → qa → release
Branch: feat/ae-0357-autopilot-idempotent-instagram-publish
Kanban Card: TBD
Created: 2026-10-13
Updated: 2026-10-13
Parent: AE-0348

## Goal

Publish an approved carousel to Instagram exactly once, durably, with retries and a queryable status.

## Problem

`POST /api/carousels/{id}/publish/instagram` is synchronous, non-idempotent and does not persist the post id (`modules/publishing/application/service.py:149`); the frontend already expects `/publish/instagram/status` which does not exist (`frontend/src/constants/api.ts:49`).

## Scope

- `InstagramPublishJob` run from the worker tick for runs in `publishing` (1 per tick).
- Idempotency: if `ig_post_id` is set → transition to `published`, no API call. If `ig_container_id` is set and < 24 h old → skip container creation, poll it and `media_publish`.
- Pre-checks: `content_publishing_limit` quota > 0; project `workflow_status == approved_for_publish`, `status == completed`, `is_public`; 2–10 slides; slide URLs from existing helper (`api/routes/carousels/helpers.py:147`) — move/expose via publishing facade if needed.
- Use existing `MetaInstagramPublisher` (`infrastructure/external/meta_instagram_publisher.py`); refactor it to return container id before publish and accept a token provider (AE-0358) instead of the static setting, keeping the existing route working.
- Persist `ig_container_id`, `ig_post_id`, `ig_permalink` (GET `/<media_id>?fields=permalink`).
- Errors: transient (5xx, rate limit, container IN_PROGRESS timeout) → retry with backoff, max 3 → `publish_failed` + notify (AE-0355). Permanent (4xx auth/format, e.g. 36003 aspect ratio) → `publish_failed` immediately with Meta error code.
- `GET /api/carousels/{id}/publish/instagram/status` (JWT, owner/editor) → `{state, ig_post_id, permalink, error}` matching what the frontend constant expects (check its consumer for the shape).
- Existing manual route: make it idempotent too (reuse the job's core function).

## Non-Goals

- Scheduling posts for later.
- Reels/stories.

## Acceptance Criteria

- [ ] WHEN the job runs twice for the same run THE Graph API `media_publish` SHALL be called at most once.
- [ ] WHEN the process crashes after container creation THE next tick SHALL reuse the container (no duplicate post).
- [ ] WHEN Meta returns a transient error THE job SHALL retry up to 3 times, then set `publish_failed` and notify.
- [ ] WHEN publish succeeds THE run SHALL be `published` with `ig_post_id` + `ig_permalink` and the owner SHALL get the link.
- [ ] WHEN the status route is called THE API SHALL return the persisted state.

## Gherkin Scenarios

```gherkin
Feature: Idempotent Instagram publish

  Scenario: Approved carousel is posted once
    Given a run in "publishing" for a released carousel with 7 slides
    When the publish job runs twice
    Then media_publish is called once
    And the run is "published" with a permalink

  Scenario: Crash after container creation
    Given a run with a stored carousel container id and no post id
    When the publish job runs
    Then no new containers are created
    And the stored container is published

  Scenario: Permanent Meta error
    Given Meta rejects the container with error 36003
    When the publish job runs
    Then the run is "publish_failed" with the Meta error code
    And the owner is notified with a Retry button
```

## Delta

### ADDED

- `backend/src/rag_backend/modules/autopilot/application/publish_job.py`
- Status route
- `backend/tests/features/autopilot_instagram_publish.feature`

### MODIFIED

- `infrastructure/external/meta_instagram_publisher.py` (split create/poll/publish, token provider)
- `api/routes/carousels/publishing.py` (idempotent manual route)
- `modules/publishing/public.py` (expose needed ops)

### REMOVED

- None.

## Affected Areas

- Backend
- API
- Database (writes)
- Tests: respx-mocked Graph API
- Frontend: none (route matches existing constant)

## Dependencies

- Blocks: AE-0356, AE-0358
- Blocked by: AE-0350

## Implementation Plan

1. Feature first.
2. Refactor publisher into steps with tests preserving current route behavior.
3. Job with idempotency branches.
4. Status route + manual-route reuse.

## Implementer Notes (read first — Cursor CLI / Grok)

- Source of truth: [docs/architecture/grokbot-autopilot.md](../../docs/architecture/grokbot-autopilot.md) and [ADR-0020](../../docs/decisions/0020-grokbot-autopilot.md). If this ticket and the doc disagree, STOP and ask — do not guess.
- Read `CLAUDE.md`, `backend/CLAUDE.md`, `backend/AGENTS.md`, `docs/architecture/module-conventions.md` before coding.
- Module rules: new code lives in `backend/src/rag_backend/modules/autopilot/` following `modules/_template/` (domain/application/infrastructure/api + `public.py` + `bootstrap.py` + `constants.py`). Other modules are reached ONLY through their `public.py`; add an import-linter contract for `autopilot` (module-conventions §7a/§7d).
- Hard rules: no magic strings (constants.py), no `Any`/`object`, ≤3 args per function (Pydantic/typed command objects), guard clauses, ≤400 lines/file, mypy strict, ruff clean, 90%+ branch coverage.
- Behavior-changing tickets: write the `.feature` file FIRST under `backend/tests/features/` and reference scenario names in test comments.
- Never commit secrets. Never push `main` (auto-deploys prod). Branch per ticket, lowercase conventional commits.
- Done = `bash scripts/ci/gate-capture.sh backend` green with the `GATES_JSON:` line pasted in the dev summary + `/qa-agent` PASS. Never pipe gates to `tail`/`head`.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked
- [ ] Double-publish impossible (crash-resume test)
- [ ] Existing publish route tests still green

## Progress Log

### 2026-10-13 00:00

Ticket created from docs/architecture/grokbot-autopilot.md (ticket #8).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

See ADR-0020.

## Blockers

None.

## Final Summary

Pending.
