# AE-0636 — A retry of a blocked content gate fixes the blocked fields instead of re-drafting the deck

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0636-autofix-targeted
Kanban Card: TBD
Created: 2026-11-21
Updated: 2026-11-21

## Goal

Retrying a carousel whose content gate blocks a few fields rewrites only those fields and keeps every valid slide.

## Problem

Prod carousel 4223b53a-643c-5b9a-8621-235e0136fee6 stayed blocked through three owner Retries on 2026-11-20. The
gate blocked only slide 8's three `summary_points[n].body` (120 to 182 characters against a 90 limit, EN using `**`
instead of `<strong>`). Each Retry is a content revise with the system note "Reason: content_quality", which names
no slide, so `revision_scope` returned the whole deck and all 9 slides were re-drafted. Every redraft brought new
violations (16, then 11, then 9) and the lowest persona score fell from 77 to 62 to 30.

The targeted field repair that runs after the review build should have fixed slide 8, but its model call is bounded
by `GATE_REPAIR_TIMEOUT_SECONDS = 180`, shorter than the fast role's own 300 s timeout plus its 300 s fallback. A slow
fast-model answer (139 s for round 1 in a dry run on prod) was cancelled before the fallback could answer, and a
failed round ended the loop, so the repair gave up with nothing changed. A dry run of the same repair on prod's stored
slides with a working model cleared all 9 violations in 2 rounds and changed only slide 8.

## Scope

- `content_fix_mode.is_fix_revision`: a content revision is a fix when the gate blocks, the deck has stored slides and
  drafts, and every active note is system-written (`feedback_source = autopilot`: an owner Retry or an autopilot
  rework). A fix skips the redraft, scoring and rebuild, runs only the targeted field repair on the stored slides and
  settles the notes (`applied` when the copy changed, `unchanged` otherwise). A note the owner writes is a rework, as
  before.
- `content_feedback_lifecycle.active_note_sources`: who wrote each active note.
- The repair loop: `GATE_REPAIR_TIMEOUT_SECONDS` 180 → 660 (longer than 300 + 300), `GATE_REPAIR_MAX_ROUNDS` 2 → 3,
  and a failed or timed-out round no longer ends the loop.
- Docs: `docs/backend/slide-copy-validators.md`.

## Non-Goals

- Do not add a new Retry kind or change the Telegram or web Retry surfaces.
- Do not change the deterministic "Fix issues" repair (`carousel_repair_service`, owner autofix).
- Do not change the field repair prompt.

## Acceptance Criteria

- [ ] A system retry of a blocked gate re-drafts no slide, asks the repair only for the blocked fields, keeps every
      other slide's copy, and the gate passes when the answers fit.
- [ ] A fix whose answers change nothing keeps the deck and records the note `unchanged`.
- [ ] An owner revise note still re-drafts the content with that note.
- [ ] A mixed (system + owner) or untagged note, a gate that does not block, a warning-only gate, or a first draft is
      not a fix.
- [ ] A failed repair round does not end the loop; the next round asks again.
- [ ] One repair round's timeout is longer than the fast timeout plus the fallback timeout.

## Repro Steps

1. Park a carousel at content with a blocking gate on one slide.
2. Press Retry (Telegram or web).
3. Before: every slide is re-drafted and the gate blocks on other fields. After: only the blocked fields change.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-11-21 11:00

Ticket created from the prod investigation of carousel 4223b53a (checkpoint state, generation events, a dry run of
the field repair on prod).

## Files Touched

- `backend/src/rag_backend/application/services/carousel/content_fix_mode.py` (new)
- `backend/src/rag_backend/application/services/carousel/content_feedback_lifecycle.py`
- `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`
- `backend/src/rag_backend/application/services/carousel/content_gate_repair.py`
- `backend/src/rag_backend/domain/constants/content_gate_repair.py`
- `backend/tests/features/content_fix_revision_ae0636.feature` (new)
- `backend/tests/features/content_gate_repair_ae0430.feature`
- `backend/tests/unit/agents/test_content_fix_revision_ae0636.py` (new)
- `backend/tests/unit/application/test_content_fix_mode_ae0636.py` (new)
- `backend/tests/unit/application/test_content_gate_repair_ae0430.py`
- `docs/backend/slide-copy-validators.md`

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
