# AE-0637 — The autopilot slide fix keeps its best attempt, scores the whole slide and outlasts slow models

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0637-slide-autofix-keep-best
Kanban Card: TBD
Created: 2026-11-21
Updated: 2026-11-21

## Goal

The autopilot slide fix keeps every fix it gets, so a Retry ends with only the issues that are really left.

## Problem

After AE-0636 shipped, the owner pressed Retry on carousel 4223b53a again (2026-11-21 15:32). Telegram ran it as a
redrive, so the content artifacts were replayed and the autopilot slide fix ran on slide 8:

- attempt 1 (fast): `model_error`;
- attempt 2 (fast): every copy rule cleared, only `voice_score_low` left;
- attempt 3 (fast): started from attempt 2's copy and broke `body_too_long` again;
- attempts 4 and 5 (reasoning): `model_error`;
- `carousel_slide_fix_noop`: nothing written, the run escalated with the original 9 violations.

Causes:

- `SLIDE_FIX_TIMEOUT_SECONDS = 120` is shorter than the fast role's 300 s and the reasoning role's 360 s own
  timeouts plus the 300 s fallback, so slow calls were cancelled and counted as model errors.
- Each attempt started from the latest copy, even when that copy was worse than an earlier one.
- An unfixed slide returned the stored copy and the service wrote only fixed slides, so attempt 2's fixes were lost.
- The loop judged the PT body or, when empty (a summary slide), only the heading, while the content phase scores the
  whole visible copy (`voice_text`), so the voice score of a rewritten summary slide could not move.

## Scope

- `SLIDE_FIX_TIMEOUT_SECONDS` 120 → 720.
- `slide_fix_loop`: track the best attempt (fewest copy rules broken, then fewest checks), start each attempt from it,
  return it for an unfixed slide marked `improved` when it breaks fewer copy rules than the stored slide, and score
  with `voice_text`.
- `SlideFixResult.improved`; `SlideFixService` writes fixed and improved slides.
- Docs: `docs/architecture/grokbot-autopilot.md`, `docs/backend/slide-copy-validators.md`.

## Non-Goals

- Do not change the Retry kinds (redrive vs revise) or the AE-0636 fix path.
- Do not change the voice floor or the slide fix prompt.

## Acceptance Criteria

- [ ] An unfixed slide whose best attempt breaks fewer copy rules is returned `improved` with that copy and score, and
      the service writes it.
- [ ] An attempt that makes the slide worse is not built on: the next attempt starts from the best copy.
- [ ] A slide no attempt improved keeps its stored copy and is not written.
- [ ] The judge reads the slide's whole visible PT copy.
- [ ] One rewrite's timeout is longer than the reasoning timeout plus the fallback timeout.

## Repro Steps

1. Park a carousel at content whose one slide breaks a copy rule and scores under the voice floor.
2. Let the autopilot slide fix run with a model that fixes the rule on one attempt and breaks it on the next.
3. Before: nothing is written. After: the best copy is written and only the voice floor is escalated.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0636 (merged).

## Progress Log

### 2026-11-21 16:00

Ticket created from the prod logs of the 15:32 Retry on carousel 4223b53a.

## Files Touched

- `backend/src/rag_backend/application/services/carousel/slide_fix_loop.py`
- `backend/src/rag_backend/application/services/carousel/slide_fix_service.py`
- `backend/src/rag_backend/application/services/carousel/slide_fix_types.py`
- `backend/src/rag_backend/domain/constants/slide_fix.py`
- `backend/tests/features/slide_autofix_keep_best_ae0637.feature` (new)
- `backend/tests/unit/application/test_autofix_escalation_ae0407.py`
- `backend/tests/unit/application/test_slide_fix_service_ae0401.py`
- `docs/architecture/grokbot-autopilot.md`
- `docs/backend/slide-copy-validators.md`

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
