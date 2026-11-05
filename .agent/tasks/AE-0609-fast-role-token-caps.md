# AE-0609 — Fast-role calls leave the reasoning model room to answer

Status: Dev Complete
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude
Agent Lane: developer → qa → release
Branch: fix/ae-0609-fast-role-token-caps
Kanban Card: TBD
Created: 2026-11-04
Updated: 2026-11-04

## Goal

No fast-role call sends a token cap that the model's reasoning can use up before it writes the answer.

## Problem

AE-0607 showed that a bound `max_tokens` reaches the OpenCode Go endpoint as `max_completion_tokens` and
replaces the model's 32000 default, and that the fast models spend that budget on reasoning first. Its
copy-budget fit answered nothing on every call. This ticket checks every other LLM call for the same fault.

### Prod measurement (Langfuse, last 7 days, read-only, taken before this ticket)

- Among GENERATION observations, the only calls with visible output 0 and reasoning exactly at a cap
  (512/1000/1024/1500/2000/2048/3000/4096/8192) were `carousel.content copy budget fit` (12/15 on
  deepseek-v4.1-flash, 5/5 on qwen3.8-flash, all at 4096), which AE-0607 fixed.
- Slide drafting reached about 5.7k reasoning tokens without being cut off.
- Cover ideas and palette generation did not appear at all.

Langfuse cannot be queried from the host this ticket was built on, so nothing here is re-measured.

## Findings

**Why slide drafting was not cut off.** The drafter binds its prompt's model block, and every active content
prompt says 32000 (`carousel/v6`, `carousel/v7`, `carousel_pov/v4`, `carousel_pov_news/v4`). The 2048 and 4096
values are in old content versions that no longer render.

**Most YAML caps are never sent.** `render_prompt` returns `(text, model_config)`, and all callers except two
drop the second value. Only four call sites bind a cap: `git grep '\.bind('` finds the drafter, the fit, cover
ideas and palette (plus `fallback_runnable_for`, which carries an existing bind over to the fallback).

**Why cover ideas and palette never appeared: they were not traced.** Neither passed a Langfuse callback.
`propagate_attributes` opens the phase span, but no generation is recorded without
`get_langfuse_runnable_config()`, and the factory, the routed model and the queue attach no handler. So
"did not show up with a cap hit" says nothing about these two calls: they could never have shown up.
`LLMService.generate` has the same gap (see Follow-ups).

**Risk.** Both were sent under the observed reasoning spend (hundreds to about 6k tokens):

- Palette (2000): a visible answer of about 450 tokens (estimate: 3 candidates) leaves 1550 for reasoning.
- Cover ideas (1500): a visible answer of about 1.1k tokens (estimate: 6 × (400 + about 150) chars at about 3
  chars per token) leaves about 400 for reasoning. A cap hit there truncates the JSON as well, which parses to
  no ideas.

### Audit

Models: fast = `deepseek-v4.1-flash`, then `qwen3.8-flash`; reasoning = `deepseek-v4-pro`, then `qwen3.8-max`.
"Sent" is what reaches the provider as `max_completion_tokens`.

| Call site | Role | Cap source | Sent | Risk | Action |
|---|---|---|---|---|---|
| Cover ideas, `CoverIdeasCompletion` | fast | `IDEAS_MAX_TOKENS` 1500 | **1500** | **Yes** | **Fixed: 32000** |
| Palette, `PaletteCompletion` | fast | `GENERATION_MAX_TOKENS` 2000 | **2000** | **Yes** | **Fixed: 32000** |
| Slide draft, `ContentDraftAgent` | fast | active content YAML, 32000 | 32000 | No | Checked |
| Copy-budget fit, `LlmCopyBudgetFitter` | fast | `carousel_copy_budget/v3`, 32000 | 32000 | No | AE-0607 |
| Persona enforce / evaluate | fast | none | 32000 | No | Checked |
| Outline, `generate_outline` / POV outline | reasoning | `carousel/v3`, `v7`, `carousel_pov*/v1`, 2048, dropped | 32000 | No | Checked |
| Hooks, `hook_candidates` / radar | reasoning | hook YAML 1024, dropped | 32000 | No | Checked |
| Caption, `_generate_caption` | fast | caption YAML 512, dropped | 32000 | No | Checked |
| EN translation | fast | none | 32000 | No | Checked |
| Gate repair, `LlmGateFieldRepairer` | fast | `carousel_gate_repair/v1` 4096, dropped | 32000 | No | Checked |
| Slide fix, `_ModelRewriter` | fast | `carousel/v1/slide_fix` 2048, dropped | 32000 | No | Checked |
| Autofix re-translate | fast | none | 32000 | No | Checked |
| Refine copy, `refine_copy` | fast | `refinement/v1/copy_rewrite` 1024, dropped | 32000 | No | Checked |
| Refine image / design, `LLMService.generate` | fast | `refinement/v1` 512 / 1024, dropped | 32000 | No | Checked |
| LinkedIn, `LinkedInPostGenerator` | fast | none | 32000 | No | Checked |
| Blog AI suggest / improve, translation | `GLM_MODEL` (corrected in AE-0610) | none; `max_tokens` argument never passed | 32000 | No | Checked |
| Blog writer draft / rewrite / judge | fast / reasoning | none | 32000 | No | Checked |
| Rubric judge, quality, source synthesis | reasoning | none | 32000 | No | Checked |
| Chat / RAG agents | `GLM_MODEL` | `rag/v1/config.yaml` 4096, file never loaded | 32000 | No | Checked |

Proof of "sent":

- HTTP body tests (`test_fast_token_caps_ae0609.py`) for cover ideas and palette on the fast queue as prod
  builds it, and for the outline, whose YAML says 2048 and which sends 32000.
- `LLMService.generate(temperature=0.2, max_tokens=777)` behind a mocked endpoint sent
  `max_completion_tokens: 32000` and `temperature: 0.7`: `with_config` puts both in the run config, not in the
  request. No caller passes `max_tokens`, so this was a one-off check, not a test.
- The other "dropped" rows come from reading the callers: `prompt, _ = render_prompt(...)` with an unbound model.

## Scope

- `IDEAS_MAX_TOKENS` and `GENERATION_MAX_TOKENS` set to 32000.
- `EmptyIdeasAnswerError` and `EmptyPaletteAnswerError`: an empty visible answer is a named model failure.
- Both completions pass the Langfuse config, so the calls become generations.
- `palette_generation_call_failed`: the palette service logs a failed call (it logged nothing before).
- Routing doc updated.

## Non-Goals

- No timeout change, no new LLM call, no gate, threshold or validator change.
- No prompt version: neither cap lives in a prompt.
- No change to any "Checked" row above.

## Acceptance Criteria

- [x] The audit table covers every LLM call site with role, cap source, what is sent, and risk.
- [x] Cover ideas and palette send `max_completion_tokens: 32000` over HTTP on the queue prod builds.
- [x] With a primary that answers nothing, the queue's next model answers and both models get the 32000.
- [x] With every model empty, cover ideas and palette log the named error and end unavailable.
- [x] Both calls reach the Langfuse handler as one generation, tagged with the actual model.
- [x] The touched tests and the cheap backend gates pass.

## Gherkin Scenarios

`backend/tests/features/fast_role_token_caps_ae0609.feature`

```gherkin
Feature: Fast-role calls leave the reasoning model room to answer (AE-0609)

  Scenario Outline: The provider receives the call's token budget
  Scenario: A prompt YAML's cap that no code binds stays off the wire
  Scenario Outline: An empty primary answer moves the call to the fallback
  Scenario: An empty cover ideas answer is a logged model failure
  Scenario: An empty palette answer is a logged model failure
  Scenario: A whitespace answer counts as empty
  Scenario: A failed palette call is logged with its error
  Scenario Outline: The call reaches Langfuse as a generation
```

## Delta

### ADDED

- `EmptyIdeasAnswerError`, `EmptyPaletteAnswerError`, `LOG_PALETTE_CALL_FAILED`.

### MODIFIED

- `IDEAS_MAX_TOKENS` 1500 → 32000; `GENERATION_MAX_TOKENS` 2000 → 32000.
- `CoverIdeasCompletion.complete` and `PaletteCompletion.complete`: traced, raise on an empty answer.
- `PaletteGenerationService._complete`: logs a failed call.
- `docs/backend/llm-model-routing.md`: which calls bind a cap, and what bounds them now.

### REMOVED

- Nothing.

## Affected Areas

- Backend: `agents/cover_prompt_prompts.py`, `agents/palette_prompts.py`, `palette_generation_service.py`,
  `domain/constants/cover_prompt_ideas.py`, `domain/constants/palette_generation.py`
- Tests: new feature and unit tests
- Observability: two new generations, one new log event
- Frontend / Database / API / Deployment: none

## Dependencies

- Related: AE-0607 (the same fault in the fit), AE-0507 (palette), AE-0509 (cover ideas), AE-0399 (queue)

## Implementation Plan

1. Audit the call sites.
2. `.feature`, then failing tests.
3. Fix.
4. Touched tests and cheap gates; PR.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-04

Audit done. Red before the fix: 11 of 12 new tests failed, on the behaviour (`1500 == 32000`, `2000 == 32000`,
`DID NOT RAISE`, no generation, no log). The twelfth is the audit proof that an unbound YAML cap stays off the
wire, which passes by design. Green after the fix.

## Files Touched

- `backend/src/rag_backend/agents/cover_prompt_prompts.py`, `agents/palette_prompts.py`
- `backend/src/rag_backend/application/services/carousel/palette_generation_service.py`
- `backend/src/rag_backend/domain/constants/cover_prompt_ideas.py`, `domain/constants/palette_generation.py`
- `backend/tests/features/fast_role_token_caps_ae0609.feature`
- `backend/tests/unit/agents/test_fast_token_caps_ae0609.py`
- `docs/backend/llm-model-routing.md`, `.agent/reports/AE-0609.dev-summary.md`

## Test Evidence

See `.agent/reports/AE-0609.dev-summary.md`. Full gate: lead's heavy slot. Mutation: CI only.

## QA Report

Pending.

## Decision Log

- **32000 for both, not a sized number.** It is the factory default that all other calls run with, so these two
  stop being special. A cap between 2k and 32k would be a guess: no reasoning figure exists for these two calls,
  because they were never traced. A runaway call is still bounded by the deadlines, at about 1.4k tokens (12 s)
  and about 10k (90 s) per attempt at the measured ~117 tok/s.
- **Constants, not prompt versions.** Both caps are code constants. The YAML model blocks of these two prompts
  have no `max_tokens`.
- **Tracing added at the two fixed sites only.** LLM calls must be traced and these two never were. Without
  it the fix cannot be checked in prod. It is one argument on a line that was changing anyway.
  `LLMService.generate` has the same gap on more callers, so it is a follow-up.
- **Keep the bind and set the constant,** rather than dropping `max_tokens` from it: the temperature is bound
  there anyway, and the cap stays explicit.
- **An empty palette answer now fails on the first attempt.** The service gives a failing call no second try,
  and an empty answer now counts as failing. Prod does not change: the queue already raises on an all-empty
  run. It only affects the non-queue routing, where an empty fallback answer used to get a second call.
- **Truncated visible answers are not detected.** A cap hit partway through the JSON is a parse failure, which
  both services already treat as no usable answer. With 32000 the cap should not cut one off.
- **The fallback path needed no change.** The queue and the routed model already treat an empty answer as a
  failure and move on. The new tests prove that with the cap bound, on both models.

## Follow-ups (not in this ticket)

- **Cover ideas' 12 s deadline is now the limit, and it may be the real problem.** At ~117 tok/s, 12 s fits about
  1.4k tokens, roughly the visible answer alone, so any real reasoning ends in a timeout, not a cap hit. The
  queue also cannot reach its fallback inside 12 s, since one slow call uses all of it. This ticket does not
  change timeouts. After this ships, read `cover_prompt_ideas_call_failed error=TimeoutError` in the logs and
  the new generations in Langfuse. If it times out, the owner has to decide on the deadline.
- **`LLMService.generate` is not traced:** blog AI suggest and improve, blog translation, LinkedIn, and refine
  image / design record no generation.
- **`LLMService.generate` ignores `temperature` and `max_tokens`:** `with_config` keeps them out of the request,
  so the blog translation, LinkedIn and refinement temperatures are not applied (all ran at 0.7).
- **The dropped YAML caps are a trap.** If a caller starts binding one (outline 2048, hook 1024, caption 512,
  slide fix 2048, refinement, gate repair 4096), the AE-0607 failure comes back.

## Blockers

None.

## Final Summary

Only four LLM calls send a token cap. Slide drafting and the copy-budget fit send 32000. Cover ideas (1500) and
palette generation (2000) were under the reasoning prod spends, and now send 32000 too. Every other YAML cap
is never sent. Cover ideas and palette also had no Langfuse generation, which is why the prod measurement could
not see them; both are traced now. An empty visible answer is a named, logged model failure. Timeouts, gates and
validators are unchanged. Cover ideas' 12 s deadline may still be too short: see Follow-ups.
