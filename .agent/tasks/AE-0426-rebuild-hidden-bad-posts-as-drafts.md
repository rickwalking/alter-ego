# AE-0426 — Rebuild hidden bad posts as drafts via the new pipeline (E)

Status: Intake
Tier: T2
Priority: P2
Type: Feature
Area: Cross-cutting
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-10-18
Updated: 2026-10-18

## Goal

Take the carousel-origin posts hidden under AE-0422's selection criteria and rebuild them as drafts
through the new writer pipeline (AE-0425), so the owner reviews each and republishes. This is the
one-off recovery of every already-published old-pipeline row.

## Problem

Every already-published carousel-origin post (10 at cutover) was assembled by the old pipeline:
carousel-slide images injected at read time, baked-in text, no owner voice. They were all hidden
(status → draft) by the orchestrator with owner approval — there is no body-length/H1 filter. They
must be regenerated as v2 drafts with the owner's voice and generated images, then reviewed.

## Scope

- A one-off operational script (`scripts/blog/rebuild_hidden_posts.py`) that selects rows by the
  **durable hide marker** written by AE-0422
  (`ai_generation_metadata.hidden_bad_post` present and `rebuilt_at` absent), independent of the
  current `status` (hiding sets `draft`; a status-based selector would immediately go empty). For
  each row it composes inputs from its carousel (research findings, outline,
  `long_form_notes`), calls the writer pipeline (AE-0425) to produce a **draft** v2 document with
  cover + section images, and leaves `status = "draft"` for owner review.
- Idempotent and resumable: after a successful rebuild, set
  `hidden_bad_post.rebuilt_at = now` (keep the marker for audit) and skip rows with `rebuilt_at`
  set; also skip rows already at `schema == "blog.v2"` with a stored quality score. A re-run never
  creates a second row per project.
- A dry-run mode listing the target rows and the marker that selected each (origin+status was the
  prod sweep; there is no content-quality filter to report).

## Non-Goals

- Auto-publishing any rebuilt post (owner reviews and publishes).
- The writer itself (AE-0425) and the cutover (AE-0423).
- Rows whose carousel no longer exists (report and skip).

## Acceptance Criteria

- [ ] AC1: The script selects exactly the rows carrying AE-0422's hide marker with no
      `rebuilt_at`, and lists them in `--dry-run`.
- [ ] AC2: For each target row, a single v2 draft is produced with a cover, one image per section,
      and stored `content.quality.voice_score` + `translations.en.quality`.
- [ ] AC3: No target row ends `status == "published"`; all remain `draft`.
- [ ] AC4: Re-running the script is a no-op for already-rebuilt rows (`rebuilt_at` set; idempotent)
      and never creates a duplicate `blog_posts` row per project.
- [ ] AC5: Rows whose carousel is missing are reported and skipped without error.
- [ ] AC6: The run is observable: a summary (selected / rebuilt / skipped / failed) and Langfuse
      traces per post.

## Gherkin Scenarios

- `backend/tests/features/blog_rebuild_hidden_ae0426.feature`.
- Scenario list: dry-run lists all marker-selected targets (including rows already at `draft`, and
  rows the old body-length/H1 filter would have missed); rebuild produces a draft with images and
  PT/EN scores; `rebuilt_at` makes the re-run a no-op; missing carousel skipped; never publishes; a
  plain draft without the marker is not selected.

## Delta

### ADDED

- `scripts/blog/rebuild_hidden_posts.py` (+ a small unit test).
- Feature spec above.

### MODIFIED

- None (uses the AE-0425 pipeline and AE-0422 criteria).

### REMOVED

- None.

## Affected Areas

- Backend: operational script
- Frontend: none
- Database: rewrites `content` of hidden rows (no schema change)
- API: none (calls the service layer)
- Tests: script unit + feature
- Docs: this ticket + a short runbook note
- Prompts/LLM: uses `blog/v1` prompts
- Observability: per-post Langfuse trace + run summary
- Deployment: run once after D ships; **not** a deploy step

## Dependencies

- Blocks: none.
- Blocked by: AE-0425 (writer + images), AE-0423 (document shape).
- Related: AE-0422 (selection criteria), QA F-04/F-05.

## Implementation Plan

1. Feature spec + script skeleton with `--dry-run`.
2. Reuse the AE-0425 generation service; select rows by the AE-0422 **durable marker**, not by
   `status = "published"` (hiding already changed the status).
3. Idempotency guard + summary output.
4. Unit + feature tests.

## QA Checklist

- [ ] Security reviewed (no secrets, no destructive delete)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (missing carousel, partial images, re-run)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-18 16:30

Ticket created from the AE-0422 plan (ADR-0025, wave E).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **Drafts, not republished.** The owner must review the new voice/images before anything goes live
  (owner decision 3).
- **Idempotent by project.** A re-run must not create a second blog row for the same carousel.

## Risk & Size

- **Risk:** Low — one-off operator script; mitigated by --dry-run, idempotency and never publishing.
- **Size:** S

## Blockers

None.

## Final Summary

Pending.
