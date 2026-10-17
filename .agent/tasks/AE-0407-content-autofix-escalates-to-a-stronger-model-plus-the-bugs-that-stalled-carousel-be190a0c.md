# AE-0407 — Content autofix escalates to a stronger model, plus the bugs that stalled carousel be190a0c

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: Cross-cutting
Owner: Claude (owner-requested hotfix)
Agent Lane: developer → qa → release
Branch: fix/ae-0407-autofix-escalation
Kanban Card: TBD
Created: 2026-10-17
Updated: 2026-10-17

## Goal

The autopilot slide fix tries the stronger reasoning model before it escalates to the owner. A
persona score is read on one 0-100 scale everywhere. A failed judge call is never stored as a
verdict. A model rewrite can clear a stale casing marker. `@handles` and URLs keep their case.
The dashboard shows the `pov_news` quote card as a card, not as JSON.

## Problem

Prod carousel be190a0c (pov_news, autopilot run f88bc343, 2026-10-17 02:25–02:33Z):

- The AE-0401 model autofix ran 3 attempts per slide on the FAST model and escalated with
  `persona_score_below_threshold`, failing slides [1, 2, 8, 9].
- Slide 1's stored persona score was **8.7** (0–10 scale), compared with the 0–100 floor 70.
- The persona judge (`PersonaAgent.evaluate_match`, FAST model) is flaky: on the same texts it
  returned `overall` 0.0, then 7.8, then 78; and 50 then 5.1. A 0.0 is a failed call/parse.
- Slide 8 could never be fixed: its only blockers were AE-0366 `casing_repairs` markers.
  `apply_answer` deep-copies the markers, so a model rewrite never cleared them.
- The casing repair turned `@taylorhbuilds` into `@Taylorhbuilds` (`_first_significant_index`
  skips `@`).
- The dashboard content review showed the AE-0406 `insight` quote card as raw JSON.

The orchestrator fixed this carousel by hand; prod is not touched by this ticket.

## Scope

1. Slide fix escalation: after `AUTOPILOT_AUTOFIX_ATTEMPTS` (3) failed FAST attempts, up to
   `AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS` (default 2, 0 = off) attempts on the REASONING model.
   Attempts numbered 1..5, the model role logged per attempt, the escalation text counts all.
2. One shared domain helper for persona scores (`rag_backend/domain/persona_score.py`): a stored
   `overall` ≤ 10 is on the 0–10 scale (×10), a 0/missing/unreadable `overall` is unscored. Used by
   `slide_fix_targets`, the autopilot snapshot and the engine's content-approve check.
   `_parse_evaluation_response` scales an `overall` ≤ 10 even when a sub-score is above 10.
3. Judge failures (error, timeout, 0.0, no `overall`) are retried once; a second failure leaves
   the slide unscored (keeps its previous score, no `voice_score_low`). 0.0 is never written.
4. A model rewrite of a field carrying a `casing_repairs` marker that passes the live
   sentence-case check drops that field's marker.
5. The sentence-case check and `capitalize_at` leave a sentence starting with an `@handle` or a
   URL alone.
6. Frontend: the content review renders `insight` as a read-only quote card in both locales.

## Non-Goals

- Do not refactor unrelated code.
- No prod data fix (the carousel was fixed by hand).
- No change to the persona judge prompt or its model role.

## Acceptance Criteria

- [ ] AC1: A slide fixed on FAST attempt 2 stops there (2 attempts, role `fast`).
- [ ] AC2: A slide still failing after 3 FAST attempts is fixed on attempt 4 by the REASONING
  model, and the gate approves.
- [ ] AC3: A slide still failing after 5 attempts escalates; the escalation text says
  "(5 fix attempts)"; attempts 1-3 log `model_role=fast`, 4-5 `model_role=reasoning`.
- [ ] AC4: With `AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS=0` the run escalates after 3 attempts and
  the reasoning model is never built.
- [ ] AC5: The setting exists (default 2, `ge=0`), is wired worker → autofixer → slide fix, and is
  named on both prod surfaces (deploy.yml, docker-compose.prod.yml) and in the autopilot-env gate.
- [ ] AC6: A stored 8.7 reads as 87 on every read path (slide fix targets, autopilot snapshot,
  content-approve check); 75 reads as 75; 0.0 reads as unscored (not low) on every read path.
- [ ] AC7: `_parse_evaluation_response` scales an `overall` ≤ 10 even when a sub-score is > 10.
- [ ] AC8: A judge call that errors, times out, or parses to 0.0 / no `overall` is retried once;
  a second failure keeps the previous score, adds no `voice_score_low`, writes no 0.0, and logs
  `persona_judge_failed`. The content phase omits an unscored slide instead of storing 0.0.
- [ ] AC9: Slide 8's case: only casing markers, rewritten correctly → markers dropped, slide
  fixed. A rewrite that still starts lowercase keeps the marker; an unanswered field keeps it.
- [ ] AC10: `@taylorhbuilds viu…` and `https://…` sentence starts are neither flagged nor
  capitalized; a normal lowercase start still is.
- [ ] AC11: The content review shows `insight` as a quote card (quote, name, `@handle · X`, no URL)
  in PT and EN with en/pt i18n keys; a malformed insight keeps the JSON fallback.

## Gherkin Scenarios

- `backend/tests/features/autofix_escalation_ae0407.feature` (items 1-5)
- `frontend/tests/features/content-review-insight-card-ae0407.feature` (item 6)

## Delta

### ADDED

- Pending.

### MODIFIED

- Pending.

### REMOVED

- None.

## Affected Areas

- Backend: autopilot slide fix loop, persona score readers, persona judge, sentence case
- Frontend: content review locale fields
- Database: none
- API: none
- Tests: unit + feature
- Docs: slide-copy-validators.md, grokbot-autopilot.md
- Prompts/LLM: the reasoning role is used for escalation attempts (no prompt change)
- Observability: `model_role` on `autopilot_slide_autofix`, `persona_judge_failed`
- Deployment: optional `AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS` (defaults to 2 on both surfaces)

## Dependencies

- Blocks: autopilot pov_news runs reaching the owner without manual fixes
- Blocked by: none
- Related: AE-0366, AE-0398, AE-0401, AE-0406

## Implementation Plan

1. Ticket + feature.
2. Persona score helper and readers; parse fix.
3. Judge retry/unscored.
4. Escalation stage in the fix loop + setting + wiring.
5. Casing marker clear; handle/URL sentence case.
6. Frontend quote card.
7. Gates, PR, CI.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-17

Ticket created from the owner brief (hotfix fast path).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending (hotfix fast path: CI Test & Coverage decides).

## Decision Log

- 2026-10-17: The escalation rewriter is a second stage of the same loop: the reasoning
  attempts start from the last usable copy and the checks it still fails, like the fast ones.
  The persona judge stays on the FAST model; only the rewriter escalates.
- 2026-10-17: `AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS` is named on both prod surfaces with a
  default of 2 and added to the autopilot-env parity gate, so the owner can turn the escalation off
  with a GitHub variable instead of a code change. `AUTOPILOT_AUTOFIX_ATTEMPTS` stays off those
  surfaces (AE-0401 decision, unchanged).
- 2026-10-17: In tests, a `slide_fix_model` override without an escalation override is used for
  both stages, so no test ever builds a real model.
- 2026-10-17: A stored `overall` that is 0, missing or not a number is "unscored" on every read
  path (it was 0, fail-closed, since AE-0364 QA r1 B1). The owner evidence shows 0.0 is a failed
  judge call, not a verdict. All readers use the same helper, so the autopilot snapshot and the
  engine's approve check still agree (the B1 concern was them disagreeing).
- 2026-10-17: A stored `overall` in (0, 10] is ×10. A real 0-100 score of 10 or less is read as a
  0-10 answer; the judge never produces such a score for on-topic copy, and it is still under 70
  only when the 0-10 answer was under 7.
- 2026-10-17: The retry-once judge is one helper (`agents/persona_judge.py`) used by the slide
  fix scorer and the content-phase scoring, so neither stores a 0.0. Its timeout is 120 s (the
  slide fix timeout).
- 2026-10-17: A casing marker is dropped only for a field the model's answer actually set (the
  same text landed in the candidate) and that passes the live check on the model's text, before
  the deterministic repair. A lowercase rewrite the repair would capitalize keeps its marker, so
  the AE-0366 intent (proper nouns may still be lowercase) holds.
- 2026-10-17: A sentence that starts with `@handle` or a URL (`http://`, `https://`, `www.`)
  counts as correctly cased: case there is the source's, not ours.

## Blockers

None.

## Final Summary

Pending.
