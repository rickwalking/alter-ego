# AE-0607 — The copy-budget fit leaves the fast model room to answer

Status: Dev Complete
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

The copy-budget fit (the shorten step before the content validation) lands rewrites in production.

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

## Root cause (measured)

Measured by the lead in Langfuse (read-only, v2 observations, generation "carousel.content copy budget fit")
for the first attempt, 15:20:29–15:23:29Z:

| Start (Z) | Latency | Model | Input tokens | Output | Reasoning | Content |
|---|---|---|---|---|---|---|
| 15:20:29.273 | 34.9 s | deepseek-v4.1-flash | 2797 | 0 | 4096 | empty |
| 15:21:04.212 | 37.8 s | deepseek-v4.1-flash | 109 (+2688 cached) | 0 | 4096 | empty |
| 15:21:42.018 | 37.8 s | deepseek-v4.1-flash | 109 (+2688 cached) | 0 | 4096 | empty |
| 15:22:19.855 | 63.3 s | qwen3.8-flash (fallback) | 2806 | 0 | 4096 | empty |

Sum **173.9 s**; the step's 180 s `wait_for` fired at 15:23:29 while the queue was re-rolling the fallback.

**The cause is the token cap.** `carousel_copy_budget/v1/fit_fields.yaml` binds `max_tokens: 4096`. Both
models are reasoning models: every call spent exactly 4096 tokens on reasoning and returned empty content.
The queue treats an empty answer as a content failure, re-rolled deepseek 3 times, then moved to the
fallback, which failed the same way. The `TimeoutError` is the outer deadline catching that loop.

- **What the provider received:** langchain-openai 1.1.14 sends a bound `max_tokens` as
  `max_completion_tokens` and drops the model's 32000 default (checked with
  `ChatOpenAI._get_request_payload`; the new test reads the HTTP body). So the request carried
  `max_completion_tokens: 4096`. Langfuse lists both 4096 and 32000 because it records the call kwarg and
  the model default; only 4096 went on the wire. That explains why the reasoning stopped at exactly 4096.
- **Speed:** deepseek ~117 reasoning tok/s (4096 in 35–38 s), qwen ~65 tok/s (4096 in 63 s).
- **Why the gate repair worked right after:** its YAML also says 4096, but `LlmGateFieldRepairer` never binds
  the model block, so it ran at the model default of 32000.

### Corrections to the first analysis

- I first wrote that the fallback "could never start inside 180 s" (the 300 s × 3 transient path). **That
  was wrong for prod:** the failures were empty answers (content class, re-rolled back to back), so the queue
  reached `qwen3.8-flash` at **+110 s**. The transient path (a hung primary) is still longer than 180 s, but
  that is not what happened.
- I called the 4096 cap "a contributing cause". The measurements show it is **the** cause.
- The first fix split the 180 s into a 120 s primary window plus a fallback call. The measured speeds show
  that slot cannot succeed: qwen needs 63 s just to reach 4096 reasoning tokens, so a 60 s window gives it
  ≈ 3.9k, less than the budget it already failed with. The split would also cut deepseek's room from ≈ 21k
  tokens (180 s × 117 tok/s) to ≈ 14k. **The split and the extra fallback call are removed.**

### The attempt loop

`fit_slides_to_budgets` breaks out of the loop when the model call fails, so `attempts: 1` of
`COPY_BUDGET_FIT_MAX_ATTEMPTS = 2`. Deliberate and kept: a second attempt after using the whole 180 s would
add another 180 s for the same outcome. Not the cause.

### `changed_slides [3,5,6]` with 0 accepted answers

Not from the model. `slides_in_locale_emphasis` (AE-0599) converts the EN `**...**` markers the drafting blob
wrote to `<strong>...</strong>` before measuring, deterministically. Slides 3, 5 and 6 had such markers. The
voice guard then re-scored them and put 5 and 6 back (score fell under 70). Expected behaviour of the
existing step; follow-up below.

## Scope

- New prompt version `carousel_copy_budget/v3/fit_fields.yaml`: same template as v1, `max_tokens: 32000`
  (what the drafting and the gate repair already run with on this endpoint). v1 is kept unchanged.
- `EmptyFitAnswerError`: an answer with no content is a named model failure, logged by the step as
  `copy_budget_fit_model_failed error=EmptyFitAnswerError` (previously an opaque `TypeError` from the parser).
- Docs: the routing guide notes token caps on reasoning models and the calls still at risk.

## Non-Goals

- No change to the content gate, its thresholds or the gate repair step.
- No timeout raised or split: the step's 180 s, the role's 300 s and the queue retries are unchanged.
- No other prompt's token cap changed (follow-ups below).
- No change to the voice guard.

## Acceptance Criteria

- [x] A fit answer lands a rewrite.
- [x] The fit renders `carousel_copy_budget/v3/fit_fields` with `max_tokens` 32000; v1 is untouched (same
      template, 4096).
- [x] The HTTP request to the OpenCode Go endpoint carries `max_completion_tokens: 32000` (and fails with
      4096 when the version is set back to v1: seeded check).
- [x] An all-reasoning empty answer (0 content, 4096 reasoning) → copy kept,
      `copy_budget_fit_model_failed` logged with `EmptyFitAnswerError`, attempts 1.
- [x] A timeout → copy kept, `TimeoutError` logged, attempts 1 (no second attempt).
- [x] The touched tests, `backend:lint`, `backend:type`, `backend:comments` pass (there is no
      `backend:complexity` gate; the other light static gates were run too).

## Gherkin Scenarios

`backend/tests/features/copy_budget_fit_token_budget_ae0607.feature`

```gherkin
Feature: The copy-budget fit leaves the fast model room to answer (AE-0607)

  Scenario: The fit lands a rewrite
  Scenario: The fit prompt does not cap a reasoning model at 4096 tokens
  Scenario: The provider receives the fit prompt's token budget
  Scenario: An all-reasoning empty answer is a model failure
  Scenario: A model that times out is not asked a second time
```

## Delta

### ADDED

- `agents/prompts/carousel_copy_budget/v3/` (fit_fields.yaml + README).
- `EmptyFitAnswerError` in `copy_budget_fit_llm.py`.

### MODIFIED

- `COPY_BUDGET_PROMPT_VERSION` v1 → v3.
- `docs/backend/llm-model-routing.md`: token caps on reasoning models.

### REMOVED

- Nothing (the primary window / fallback call of the first fix never reached main).

## Affected Areas

- Backend: `copy_budget_fit_llm.py`, `domain/constants/copy_budget_fit.py`
- Tests: new feature + unit tests; the existing fitter test's expected `max_tokens`
- Prompts/LLM: new `carousel_copy_budget/v3/fit_fields.yaml`
- Observability: the failure log names `EmptyFitAnswerError`
- Frontend / Database / API / Deployment: none

## Dependencies

- Related: AE-0588 (the fit step), AE-0599 (emphasis conversion), AE-0391 / AE-0399 (routing, queue)

## Implementation Plan

1. Ticket + root cause.
2. `.feature`, then failing tests.
3. Fix.
4. Touched tests + light gates; PR.
5. Lead's Langfuse evidence: correct the root cause, drop the split, add the provider-body and empty-answer
   tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-03

Ticket created; first root cause (deadline order) written before the code change, from code reading only.
Prod ssh (publickey denied) and Langfuse (no keys) were not reachable from the Pi.

### 2026-11-03 (later)

First fix: 120 s primary window + fallback call inside the 180 s, and prompt v3. PR #346 opened; merged
main twice (ae-0600 conflict in phase_artifact_runner.py resolved; ae-0601 clean). CI green on 3d35caac,
mutation included.

### 2026-11-03 (evidence)

The lead's Langfuse measurements showed every call spent the full 4096 cap on reasoning and answered nothing,
and the fallback did run (+110 s). Root cause corrected to the token cap. The split and the fallback call were
removed: the measured speeds show the fallback slot could not succeed. Kept: prompt v3. Added: the named
empty-answer error, a test that reads the HTTP body for `max_completion_tokens`, and the empty-answer test.

## Files Touched

- `backend/src/rag_backend/application/services/carousel/copy_budget_fit_llm.py`
- `backend/src/rag_backend/domain/constants/copy_budget_fit.py`
- `backend/src/rag_backend/agents/prompts/carousel_copy_budget/v3/{fit_fields.yaml,README.md}`, `../README.md`
- `backend/tests/features/copy_budget_fit_token_budget_ae0607.feature`
- `backend/tests/unit/application/test_copy_budget_fit_token_budget_ae0607.py`
- `backend/tests/unit/application/test_content_budget_step_ae0588.py` (expected `max_tokens` 4096 → 32000)
- `docs/backend/llm-model-routing.md`, `.agent/reports/AE-0607.dev-summary.md`

## Test Evidence

See `.agent/reports/AE-0607.dev-summary.md`. Full gate: lead's heavy slot. Mutation: CI only.

## QA Report

Pending.

## Decision Log

- **Drop the 120/60 split.** Measured qwen ~65 tok/s: a 60 s fallback window ≈ 3.9k reasoning tokens, less
  than the 4096 it already failed with; the split would cut deepseek's room from ≈ 21k to ≈ 14k tokens. The
  queue already reaches the fallback on empty answers. No new LLM call is needed for the measured cause.
- **32000, not a number in between.** It is the factory default the drafting and the gate repair run with on
  this endpoint. At ~117 tok/s the 180 s deadline (≈ 21k tokens) is now the outer bound. The deadline is not
  raised.
- **Name the empty answer.** `EmptyFitAnswerError` makes the failure log say what happened; with the queue,
  empties are retried inside the queue and end as its own error, so this mainly covers the non-queue routing.
- **Keep `break` after a failed attempt** (see the attempt loop above).
- **First analysis was from code alone** (prod and Langfuse unreachable from the Pi) and was wrong about the
  failure class. Corrected above, not deleted.

## Follow-ups (not in this ticket)

- **Other fast-role calls bound under 4096**, at risk of the same all-reasoning empty answer:
  - cover prompt ideas: `CoverIdeasCompletion` binds `IDEAS_MAX_TOKENS = 1500`
    (`domain/constants/cover_prompt_ideas.py`), on `fast_llm_service`;
  - palette generation: `PaletteCompletion` binds `GENERATION_MAX_TOKENS = 2000`
    (`domain/constants/palette_generation.py`), on `fast_llm_service`.
  - Checked and not at risk today: the content-gate repair (`field_repair.yaml` says 4096 but the repairer
    does not bind it, so it runs at 32000; it would fail like this if someone starts binding it); the hook,
    caption, title and slide-fix prompts (rendered with the model block discarded); the current content
    prompts (32000).
- A hung primary (transient path: 300 s per call, 3 tries) is still longer than the fit's 180 s, so the queue
  cannot reach its fallback in that case. Not observed; measure before changing.
- The voice guard reverted slides 5 and 6 whose only change was the deterministic `**` → `<strong>`
  conversion; re-scoring an emphasis-only change looks like scorer noise.
- After this ships: check `copy budget fit` in Langfuse for the reasoning tokens deepseek actually uses with
  the 32000 cap, and whether it stays well inside 180 s.

## Blockers

None.

## Final Summary

Every fit call spent the prompt's 4096-token cap on reasoning and answered nothing: 3 × deepseek, then the
qwen fallback, 173.9 s, until the step's 180 s deadline. The fit prompt v3 lifts the cap to 32000. An empty
answer is now a named, logged model failure. Deadlines, the gate, the repair and the voice guard are unchanged.
