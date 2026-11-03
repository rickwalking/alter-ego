# AE-0607 — The copy-budget fit reaches the fallback model before its deadline

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Worker (Pi)
Agent Lane: developer → qa → release
Branch: fix/ae-0607-copy-budget-fit-timeout
Kanban Card: TBD
Created: 2026-11-03
Updated: 2026-11-03

## Goal

The copy-budget fit step (the shorten step before the content validation) lands rewrites in production. When
the primary fast model is slow, the fallback model answers inside the same 180 s budget instead of the step
giving up.

## Problem

POV QA run in prod on 2026-11-03 (project `dadbe2fd`, since purged):

| Time (UTC) | Event | Detail |
|---|---|---|
| 15:20:29 | `copy_budget_fit_attempt` | 6 fields |
| 15:23:29 | `copy_budget_fit_model_failed` | `TimeoutError`, exactly 180 s after the attempt |
| | `copy_budget_fit_done` | attempts 1, asked 6, accepted 0, still_over 6, changed_slides [3,5,6] |
| | `copy_budget_fit_voice_reverted` | slides [5,6] |
| 15:46:00 | `copy_budget_fit_attempt` | 7 fields |
| 15:49:00 | `copy_budget_fit_model_failed` | `TimeoutError`, exactly 180 s |
| | `copy_budget_fit_done` | accepted 0, still_over 7 |

Both times `content_gate_repair_done` fixed the overruns afterwards (blocking false). The fit step runs on
every POV carousel's copy and has never landed a rewrite in prod.

## Root cause (written before the code change)

### 1. Deadline order: the outer 180 s kills the call before the fallback can run

The fit's model call is wrapped three layers deep:

| Layer | Where | Deadline |
|---|---|---|
| Fit attempt (outer) | `copy_budget_fit._ask` → `asyncio.wait_for` | `COPY_BUDGET_FIT_TIMEOUT_SECONDS` = **180 s** |
| Fast role, one call on one model | `ModelQueueChatModel._call` (prod: `LLM_MODEL_QUEUE_FAST=go:deepseek-v4.1-flash,go:qwen3.8-flash`) | `role_timeout(fast)` = `LLM_TIMEOUT_FAST_SECONDS` = **300 s** |
| Primary before the queue moves on | `_after_failure` / `_retry_wait` | timeout = transient: `QUEUE_TRANSIENT_TRIES` = 3 tries, backoff 2 s + 4 s → **≥ 906 s**; empty answer = content: 3 back-to-back re-rolls |
| Fallback (`qwen3.8-flash`) | second queue entry | starts only after the primary gave up |

So the fallback can start at the earliest **906 s** after a primary that keeps timing out, and never before
**300 s** for even one timed-out primary call. The outer deadline fires at **180 s**, cancels the primary
mid-call, and the fallback is unreachable by construction. Both prod failures took **exactly 180 s**: that is
the outer `wait_for`, not the role deadline (a role timeout would take ≥ 300 s and log `llm_model_retry`).
The non-queue routing (`RoutedChatModel`, 5 attempts × 300 s before the fallback) has the same order.

### 2. Model latency: not measurable here, estimated

- **Measurement attempted, not possible from this machine:** `ssh root@206.189.180.85` answers
  `Permission denied (publickey)` for the Pi's key; no Langfuse keys exist in the worktree or the main
  checkout (only `.env.example`). So no trace or log timing beyond the brief's numbers.
- **Request size:** a 7-field request rendered through `carousel_copy_budget/v1/fit_fields` with a 3,000-char
  style guide is **≈ 10,000 chars ≈ 2.5–3k input tokens**. The answer is ≈ 7 × 200 chars ≈ **400 content
  tokens**. The YAML binds `max_tokens: 4096`, `temperature: 0.3`.
- **Model speed** (`docs/backend/llm-model-routing.md`, prod endpoint benchmarks): `deepseek-v4.1-flash`
  answered a single-slide JSON with **2.2–2.5k output tokens in 14–18 s (~150 tok/s)**; most of those tokens
  are reasoning (the non-reasoning `glm-5.3-flash` used 0.2k for the same answer). At that speed even a call
  that uses the whole 4096-token cap finishes in **~28 s**. `qwen3.8-flash` answered strict JSON in **9–11 s**.
- **Conclusion:** a healthy primary answers this request in well under a minute; prod took **> 180 s twice**
  (≥ 6× the cap-bound estimate). The primary was slow or stuck on these calls; why exactly cannot be measured
  here. Two candidates, both consistent with the evidence:
  - endpoint latency on `deepseek-v4.1-flash` (drafts of ~4k chars have taken 13–134 s on it);
  - the 4096 cap: the fit is the only fast-role call in this flow that binds a 4096 cap. A reasoning model
    that spends the cap thinking returns empty content, which the queue re-rolls 3 times on the same model
    before moving to the fallback. The gate repair, on the same queue and the same field shape, runs
    unbound (the factory's 32000) and succeeded minutes after both fit failures.
  Whatever the cause, item 1 means the fallback never gets a turn.

### 3. The attempt loop: one attempt after a timeout is by design

`fit_slides_to_budgets` breaks out of the loop when `_ask` returns None (any model failure), so
`attempts: 1` of `COPY_BUDGET_FIT_MAX_ATTEMPTS = 2`. That is deliberate: a second attempt on the same model
that just used the whole budget would add another 180 s for the same outcome. It is not the cause; with the
fallback reachable inside the attempt, a fallback answer keeps the loop going to the second attempt.

### 4. `changed_slides [3,5,6]` with 0 accepted answers

Not from the model. `slides_in_locale_emphasis` (AE-0599) converts the EN `**...**` markers the drafting blob
wrote to `<strong>...</strong>` before measuring, deterministically. Slides 3, 5 and 6 had such markers, so
they "changed". The voice guard then re-scored them and put 5 and 6 back (score fell under 70). Expected
behaviour of the existing step; the voice-score drop on an emphasis-only change is noted as a follow-up below,
out of scope here.

## Scope

- Split the unchanged 180 s fit budget: the primary gets a window of
  `COPY_BUDGET_FIT_PRIMARY_SECONDS = 120 s`; when it times out (or answers unparseable JSON) the role's
  fallback (`fallback_runnable_for(fast)`: the rest of the queue, i.e. `qwen3.8-flash`) gets the remaining
  60 s, still inside the outer 180 s. Logged as `copy_budget_fit_fallback_used`; Langfuse-traced under the
  same `copy budget fit` run name.
- A new prompt version `carousel_copy_budget/v3/fit_fields.yaml`: same template, `max_tokens: 32000` (what
  the gate repair and the drafting already run with on this queue). v1 is kept unchanged.
- The orchestrator wires the fitter with the fast role's fallback.

## Non-Goals

- No change to the content gate, its thresholds or the gate repair step.
- No timeout raised: the outer 180 s, the role 300 s and the queue retries are unchanged.
- No change to the voice guard.

## Acceptance Criteria

- [x] A fit answer lands a rewrite (existing scenario still green).
- [x] A primary slower than its window → the fallback answers inside the 180 s → the rewrite lands, and the
      loop goes on to its second attempt when fields are still over.
- [x] Primary and fallback both fail → the copy is kept, `copy_budget_fit_model_failed` is logged, attempts 1.
- [x] Without a fallback the primary keeps the whole 180 s (no inner window).
- [x] The fit renders `carousel_copy_budget/v3/fit_fields`; v1 is untouched.
- [x] The touched tests, `backend:lint`, `backend:type`, `backend:comments` pass (there is no
      `backend:complexity` gate; the other light static gates were run too).

## Gherkin Scenarios

`backend/tests/features/copy_budget_fit_fallback_ae0607.feature`

```gherkin
Feature: The copy-budget fit reaches the fallback model before its deadline (AE-0607)

  Scenario: The fit lands a rewrite
  Scenario: The primary model is slow and the fallback answers
  Scenario: The fallback answer keeps the attempts going
  Scenario: Both models fail and the copy is kept and logged
  Scenario: Without a fallback the primary keeps the whole budget
  Scenario: The fit prompt does not cap a reasoning model at 4096 tokens
```

## Delta

### ADDED

- `COPY_BUDGET_FIT_PRIMARY_SECONDS`, `LOG_COPY_BUDGET_FIT_FALLBACK_USED` constants.
- `LlmCopyBudgetConfig.fallback` / `primary_seconds`; the fitter's primary window and fallback call.
- `agents/prompts/carousel_copy_budget/v3/` (fit_fields.yaml + README).

### MODIFIED

- `COPY_BUDGET_PROMPT_VERSION` v1 → v3.
- `llm_budget_fitter` takes the fallback; `PhaseArtifactRunnerConfig.budget_fit_fallback` carries it; the
  orchestrator passes `fallback_runnable_for(roles.fast)`.
- `docs/backend/llm-model-routing.md`: a note on step deadlines shorter than the role's.

### REMOVED

- Nothing.

## Affected Areas

- Backend: `copy_budget_fit_llm.py`, `content_budget_step.py`, `carousel_editorial_orchestrator.py`,
  `domain/constants/copy_budget_fit.py`
- Tests: new feature + unit tests; the existing fitter test's expected `max_tokens`
- Prompts/LLM: new `carousel_copy_budget/v3/fit_fields.yaml`
- Observability: `copy_budget_fit_fallback_used` log; fallback run traced under `copy budget fit`
- Frontend / Database / API / Deployment: none

## Dependencies

- Related: AE-0588 (the fit step), AE-0599 (emphasis conversion), AE-0391 / AE-0399 (routing, queue)

## Implementation Plan

1. Ticket + root cause (this file).
2. `.feature`, then failing tests (primary slow → fallback answers; attempt count after a timeout).
3. Fix: primary window + fallback in the fitter, orchestrator wiring, prompt v3.
4. Touched tests + lint/type/comments/complexity gates; PR.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-03

Ticket created; root cause written before the code change.

### 2026-11-03 (later)

`.feature` and failing tests first, then the fix. HEAD reproduced the prod shape in a scaled scratch repro
(one deepseek call, `TimeoutError`, attempts 1, accepted 0); the branch lands the rewrite through the
fallback. The first wiring (orchestrator importing `llm_budget_fitter`) raised the agents → application
import count (`backend:imports`, `backend:arch-ratchet` red); moved to a `PhaseArtifactRunnerConfig` field
instead of growing the baseline. Light gates green; full gate left to the lead's heavy slot.

## Files Touched

- `backend/src/rag_backend/application/services/carousel/copy_budget_fit_llm.py`
- `backend/src/rag_backend/application/services/carousel/content_budget_step.py`
- `backend/src/rag_backend/application/services/carousel/phase_artifact_runner.py`
- `backend/src/rag_backend/agents/carousel_editorial_orchestrator.py`
- `backend/src/rag_backend/domain/constants/copy_budget_fit.py`
- `backend/src/rag_backend/agents/prompts/carousel_copy_budget/v3/{fit_fields.yaml,README.md}`, `../README.md`
- `backend/tests/features/copy_budget_fit_fallback_ae0607.feature`
- `backend/tests/unit/application/test_copy_budget_fit_fallback_ae0607.py`
- `backend/tests/unit/application/test_content_budget_step_ae0588.py` (expected `max_tokens` 4096 → 32000)
- `docs/backend/llm-model-routing.md`, `.agent/reports/AE-0607.dev-summary.md`

## Test Evidence

See `.agent/reports/AE-0607.dev-summary.md`: 12 new tests, 309 touched tests passed, 15 light backend gates
pass individually (GATES_JSON there). Full gate: lead's heavy slot. Mutation: CI only.

## QA Report

Pending.

## Decision Log

- **Split, don't raise.** The fix keeps the 180 s total and gives the primary 120 s, the fallback 60 s.
  120 s is ~4× the cap-bound estimate of a healthy primary (~28 s); 60 s is ~5× the fallback's slowest
  benchmark (9–11 s) and leaves room for a 7-field answer. No timeout is raised (none could be measured).
- **Fallback on timeout and on unparseable JSON only.** Any other error (e.g. `AllModelsUnavailableError`)
  already went through the whole queue, fallback included, so a second fallback call would repeat it.
- **No new LLM call on the happy path.** The fallback call replaces the primary only when the primary failed;
  it is the call the routing design (AE-0391/0399) already intends, which the outer deadline made unreachable.
- **Keep `break` after a total failure** (attempts 1): see root cause 3.
- **Prompt v3 with `max_tokens: 32000`.** Not proven to be the cause (cannot measure), but the only
  difference between the failing fit and the succeeding gate repair on the same queue, and cheap: the gate
  repair and drafting already run at 32000. With the window/fallback split it is bounded either way. A new
  version folder (v3) because v2 already exists for `slide_limits`; v1 is not edited.
- **Prod and Langfuse unreachable from the Pi** (ssh publickey denied, no Langfuse keys): latency is
  estimated, not measured, and said so.

## Follow-ups (not in this ticket)

- The content-gate field repair has the same shape (180 s `wait_for` around a fast-role call whose fallback
  is ≥ 906 s away). Out of scope here (the brief forbids touching the repair step); it worked in this run.

- The voice guard reverted slides 5 and 6 whose only change was the deterministic `**` → `<strong>`
  conversion; re-scoring an emphasis-only change looks like scorer noise. Worth its own ticket.
- Measure `copy budget fit` latency per model in Langfuse after this ships (primary vs fallback).

## Blockers

None.

## Final Summary

The fit's 180 s attempt deadline cancelled a slow primary before the fast role (300 s per call, 3 tries)
could reach its fallback, so the fallback never ran and no rewrite landed. The attempt now gives the
primary 120 s and the role's fallback the rest of the same 180 s; the fit prompt v3 lifts the 4096 token
cap to the 32000 the gate repair runs with. Nothing else changed.
