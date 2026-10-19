# AE-0433 — Autopilot escalates a passing run when the persona judge times out

Status: Dev Complete
Tier: T1
Priority: P1
Type: Bug
Area: Backend
Owner: Claude (orchestrator hotfix, 2026-10-19)
Agent Lane: developer → qa → release
Branch: feat/ae-0433-autopilot-unscored-judge
Kanban Card: TBD
Created: 2026-10-19
Updated: 2026-10-19

## Goal

A persona judge that times out or gives no score never escalates an autopilot run as
`persona_score_below_threshold`: it is retried on the next model of the role's queue, the run
waits for a re-score on the next tick, and only a judge that stays unavailable escalates, with
its own reason `persona_judge_unavailable`.

## Problem

Prod 2026-10-19, run `8e484fe5`, carousel `5344b6c6`, phase `content`, with
`LLM_MODEL_QUEUE_FAST=sidecar:opencode/deepseek-v4.1-flash-free,go:...`:

- `persona_judge_failed` attempt 1 `error:TimeoutError`, attempt 2 `unscored: true` (twice).
- `autopilot_slide_autofix` slides 3 and 7 end `fixed` (`rules_after: []`);
  `carousel_slide_fix_applied` `still_failing: []`.
- `autopilot_slide_autofix_escalated` `failing_slides: []` → run `escalated`,
  `persona_score_below_threshold`, Telegram escalation sent.

### Root causes (file:line on `origin/main`, c9aac8162)

1. **The stale low score is re-persisted and re-read.** When the judge gives no score,
   `slide_fix_loop._rescore` (`application/services/carousel/slide_fix_loop.py:131-142`)
   keeps the slide's previous score and adds no voice issue, so the attempt is `fixed`
   (`:208`). `SlideFixResult.score` is that old score (`:225-243`) and
   `slide_fix_service._scores_patch` (`slide_fix_service.py:97-111`) writes it back. The
   autopilot step re-reads the gate (`modules/autopilot/application/slide_autofix.py:174-178`),
   `snapshot._persona_score` → `lowest_overall` still returns the old 55
   (`domain/snapshot.py:87-95`), `policy._content` returns `REASON_PERSONA_SCORE`
   (`domain/policy.py:152-153`), `needs_model_fix(fresh)` is true and `_escalate`
   (`slide_autofix.py:136-144`, called at `:179`) escalates with `failing_slides == []`.
2. **The judge's retry never reached the next queue model.** `judge_voice`
   (`application/services/carousel/persona_judge.py:36-62`) wraps each call in
   `asyncio.wait_for(PERSONA_JUDGE_TIMEOUT_SECONDS=120)`, and the fast queue's per-model
   timeout is also 120 s (`chat_model_factory.role_timeout`, `ModelQueueChatModel._call`).
   The outer timeout fires during the first (slow sidecar) model, so both attempts timed out
   on that model and the queue's `go:` fallback was never tried.

## Scope

- `persona_judge.judge_voice(judge, text, fallback)`: the retry runs on `fallback`; the
  editorial slide fix builds it as the persona on `llm.as_fallback()` (the rest of the queue,
  or the routed model's fallback) — `carousel_slide_fix._fallback_judge`.
- Slide fix loop: a fixed slide whose copy was not judged returns `unscored_ticks` (> 0). The
  persisted `persona_scores` entry keeps its old `overall` and gets `rescore_pending: true`,
  `unscored_ticks: N`. Next tick, `select_targets` reads the ticks and `fix_slide` re-scores
  the current copy before any rewrite: pass → fixed as is (marker cleared); low → rewrite
  loop with the real score; no score → `N + 1`.
- Autopilot step: when the re-read gate fails only on `persona_score_below_threshold`, with
  no failing slide, no unfixable rule and some unscored slides, it returns `WAIT`
  (`persona_rescore_pending`, the run stays `generating`) instead of escalating; once a slide
  reaches `AUTOPILOT_PERSONA_UNSCORED_MAX_TICKS` (default 3) it escalates
  `persona_judge_unavailable` with the slides listed and a Telegram text.

## Non-Goals

- Loosening the persona floor (70) or any quality gate: a stale score is never dropped, the
  gate still reads it until a real score replaces it.
- Changing model routing config / the queue env (the prod queue was already switched to
  Go-only on 2026-10-19 20:26Z by the orchestrator).
- The content-phase scoring (`phase_artifact_runner._score_slides`) already omits an
  unscored slide (AE-0407); untouched.

## Acceptance Criteria

- [x] AC1: a judge timeout on the first model is retried on the next model of the role's
  queue; a score there is used (`test_the_retry_goes_to_the_next_model_of_the_queue`,
  flow `test_timeout_then_fallback_score_approves` → gate approved).
- [x] AC2: an unscored judge after a passing fix leaves the run `generating`, no
  `autopilot_slide_autofix_escalated`, slide marked `rescore_pending` with 1 tick.
- [x] AC3: the next tick re-scores the pending slide without a rewrite and approves when the
  score passes; a low re-score goes back to the rewrite loop.
- [x] AC4: a judge unscored for `AUTOPILOT_PERSONA_UNSCORED_MAX_TICKS` ticks escalates
  `persona_judge_unavailable`, never `persona_score_below_threshold`.
- [x] AC5: a real low score still escalates `persona_score_below_threshold` listing the slide.
- [x] AC6: `autopilot_slide_autofix_escalated` is not emitted with `failing_slides == []`
  for the unscored case (an unfixable carousel-wide rule still escalates as before).
- [x] AC7: backend gates green locally except mutation (hotfix fast path; CI mutation is the
  source of truth).

## Gherkin Scenarios

Full scenarios: `backend/tests/features/autopilot_unscored_judge_ae0433.feature`.

```gherkin
Feature: An unscored persona judge never escalates a passing run (AE-0433)
  Scenario: A judge timeout on the first model is retried on the next model of the queue
  Scenario: Judge timeout then success on the fallback approves the gate
  Scenario: An unscored judge leaves the run generating and marks the slide for a re-score
  Scenario: A pending slide is re-scored on the next tick without a rewrite
  Scenario: A judge that stays unavailable escalates with its own reason
  Scenario: A real low score still escalates on the voice floor
  Scenario: A re-score that is still low goes back to the rewrite loop
```

## Delta

### ADDED

- `backend/tests/features/autopilot_unscored_judge_ae0433.feature`
- `backend/tests/unit/application/test_autopilot_unscored_judge_flow_ae0433.py` (real engine + runner)
- `backend/tests/unit/application/test_unscored_judge_ae0433.py`
- `backend/tests/unit/modules/autopilot/test_unscored_judge_step_ae0433.py`

### MODIFIED

- `application/services/carousel/persona_judge.py` (fallback judge on the retry)
- `application/services/carousel/slide_fix_loop.py` (stale re-score, unscored ticks)
- `application/services/carousel/slide_fix_targets.py` (`unscored_ticks`)
- `application/services/carousel/slide_fix_service.py` (pending marker in `persona_scores`)
- `application/services/carousel/slide_fix_types.py`, `domain/constants/slide_fix.py`
- `modules/editorial/infrastructure/carousel_slide_fix.py` (fallback judge, report ticks)
- `modules/autopilot/application/slide_autofix.py` (wait / `persona_judge_unavailable`)
- `modules/autopilot/domain/autofix.py`, `infrastructure/content_autofixer.py`,
  `autofix_constants.py`, `pov_constants.py` (Telegram text), `bootstrap.py`
- `infrastructure/config/settings.py`, `bootstrap/autopilot_worker_factory.py`
  (`AUTOPILOT_PERSONA_UNSCORED_MAX_TICKS`)
- `tests/unit/application/test_autofix_escalation_ae0407.py` (the unscored rewrite's entry
  now carries the AE-0433 re-score marker; the kept score 50 is still asserted)
- `docs/backend/slide-copy-validators.md`

### REMOVED

- None.

## Affected Areas

- Backend: autopilot content gate, carousel slide fix, persona judge.
- Database: none (checkpoint JSONB `persona_scores` entries may carry two extra keys; the
  frontend reads only `overall`).
- API: none. Prompts/LLM: none (one judge call may run on the queue's next model).
- Observability: new log `autopilot_slide_autofix_unscored`; `persona_judge_failed` gets a
  `fallback` field; `carousel_slide_fix_applied` gets `unscored`.

## Dependencies

- Related: AE-0399 (model queue), AE-0401/0407 (autopilot slide fix, judge retry).

## QA Checklist

- [x] Security reviewed (no new input surface)
- [x] Code quality reviewed (ruff/mypy strict, functions small)
- [x] Acceptance criteria validated (tests per scenario)
- [x] Edge cases tested (no scorer, raising scorer, unchanged copy, rule + stale voice,
  non-int ticks, bare-number entries, unfixable rules, unfixed slides)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-19

Root causes traced from the prod log sequence to file:line; fix + tests implemented on the
hotfix fast path.

## Files Touched

See Delta.

## Test Evidence

Hotfix fast path, each gate via `gate-capture.sh backend:<gate>`. DB gates SKIP locally (no
Postgres); the suite was run directly (5791 passed, 14 skipped, 93% total) and diff-cover
directly (100%). Python 3.11 compile/import OK. Mutation deferred to CI. Details:
`.agent/reports/AE-0433.dev-summary.md`.

GATES_JSON: {"pass":17,"fail":0,"skip":5,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"SKIP"},{"gate":"backend:diff-cover","status":"SKIP"},{"gate":"backend:migrations","status":"SKIP"},{"gate":"backend:schema-drift","status":"SKIP"},{"gate":"backend:mutation","status":"SKIP"}]}

## QA Report

Pending external QA.

## Decision Log

- **Stale score kept, marked, re-scored** instead of dropping it: dropping the old low score
  would let the gate approve copy no judge ever scored (a floor loosening). Keeping it with
  `rescore_pending` keeps the gate closed until a real score arrives.
- **Counter in the checkpoint's `persona_scores` entry**, not a new `autopilot_runs`
  column: no migration on a hotfix, and the count lives next to the score it qualifies.
- **The threshold check lives in the autopilot adapter** (`content_autofixer`, configured by
  `AUTOPILOT_PERSONA_UNSCORED_MAX_TICKS`), so `runner.py` (399 lines) is untouched.
- **An unfixable carousel-wide rule with no failing slide still escalates** (that is a real
  failure, listed in the escalation); only the unscored case waits.
- **A slide that never had a score** is not marked (nothing stale to re-score).

## Blockers

None.

## Final Summary

Pending QA / merge.
