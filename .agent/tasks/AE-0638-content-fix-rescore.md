# AE-0638 — A fix revision voice-scores the slides it rewrote

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0638-rescore-fixed-slides
Kanban Card: TBD
Created: 2026-11-21
Updated: 2026-11-21

## Goal

After a fix revision, the gate judges each rewritten slide on its own new copy's voice score.

## Problem

Prod carousel 4223b53a, Retry at 2026-11-21 17:21: the AE-0636 fix path rewrote slide 8's summary bodies and the
content gate went from 9 violations to 0. The fix path skipped persona scoring, so `persona_scores.slide_8` stayed
at 66 for the old copy. The autopilot read 66 < 70, rewrote the slide 5 times for voice (each attempt broke the
90-character limit again, so AE-0637 kept the valid copy) and escalated on the voice floor alone. The valid copy was
never scored.

## Scope

- `PhaseArtifactRunner._fix_content_gate`: after the field repair, voice-score the drafts through the content
  phase's scorer (`score_slide_voices`); a slide whose copy kept its fingerprint keeps its score, so only rewritten
  slides reach the judge.
- Docs: `docs/backend/slide-copy-validators.md`.

## Non-Goals

- Do not change the voice floor, the judge or the autopilot slide fix.

## Acceptance Criteria

- [ ] A fix revision that rewrites a slide sends only that slide's new copy to the judge and stores the new score.
- [ ] Every slide the fix did not touch keeps its stored score.

## Repro Steps

1. Park a carousel at a blocked content gate with stored voice scores.
2. Retry (system note) so the fix rewrites one slide.
3. Before: the rewritten slide keeps its old score. After: it is scored again.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0636, AE-0637 (merged).

## Progress Log

### 2026-11-21 18:00

Ticket created from the 17:21 Retry on carousel 4223b53a.

## Files Touched

- `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`
- `backend/tests/features/content_fix_rescore_ae0638.feature` (new)
- `backend/tests/unit/agents/test_content_fix_revision_ae0636.py`
- `docs/backend/slide-copy-validators.md`

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
