# AE-0610 — LLMService sends the requested temperature and records its calls

Status: Dev Complete
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude
Agent Lane: developer → qa → release
Branch: fix/ae-0610-llm-service-params-and-tracing
Kanban Card: TBD
Created: 2026-11-04
Updated: 2026-11-04

## Goal

The temperature a caller asks `LLMService.generate` for reaches the provider, and every call is a Langfuse
generation.

## Problem

`AnthropicLLMService.generate` passed `temperature` and `max_tokens` through `with_config`, which puts them in the
run config and not in the request. A mocked call asking for `temperature=0.2, max_tokens=777` sent 0.7 and 32000
(found in AE-0609). So blog translation (0.2), the design refinement (0.3) and LinkedIn (0.8) all ran at 0.7.

None of these calls passed a Langfuse callback, so none recorded a generation.

## Findings

### Caller audit

No caller passes `max_tokens`, so all of them send 32000 today, and all of them keep doing so.

"Fallback" is what happens to an empty answer. Models: fast = `deepseek-v4.1-flash`, then `qwen3.8-flash` (prod
queue); role-less = `GLM_MODEL`, default `glm-5.3`.

| Caller | Wiring | Model | Temperature asked | `max_tokens` | Sent before | Sent now | Fallback |
|---|---|---|---|---|---|---|---|
| Blog suggest, `BlogPostAIService.suggest` | `container.llm_service()` | role-less | 0.7 | none | 0.7 / 32000 | 0.7 / 32000 | **None** |
| Blog improve, `BlogPostAIService.improve` | `container.llm_service()` | role-less | 0.7 | none | 0.7 / 32000 | 0.7 / 32000 | **None** |
| Blog translation, `BlogTranslationService` | `container.llm_service()` | role-less | 0.2 | none | **0.7** / 32000 | **0.2** / 32000 | **None** |
| Conversation title | `container.llm_service()` | role-less | default 0.7 | none | 0.7 / 32000 | 0.7 / 32000 | **None** |
| Refine image, `regenerate_slide_image` | `fast_llm_service` (agent tool) | fast | 0.7 | none | 0.7 / 32000 | 0.7 / 32000 | Queue |
| Refine design, `refine_carousel_design` | `fast_llm_service` (agent tool) | fast | 0.3 | none | **0.7** / 32000 | **0.3** / 32000 | Queue |
| LinkedIn, `LinkedInPostGenerator` | `fast_llm_service` | fast | 0.8 | none | **0.7** / 32000 | **0.8** / 32000 | Queue |
| `extract_json_with_repair` | no caller in `src` | n/a | 0.2 | none | n/a | n/a | n/a |
| `generate_stream` | no caller in `src` | n/a | n/a | none | n/a | n/a | n/a |

Two corrections to the AE-0609 audit table, which says "fast" for all of these:

- Blog suggest, improve and translation run on the role-less model, not on the fast role. It has no fallback and no
  per-call timeout.
- `get_carousel_refinement` in `api/routes/carousels/deps.py` also builds the refinement on the role-less service,
  but only the agent tools call the two methods that use `generate`, and those are built on the fast role. So
  "fast" is right for both refine rows.

Every model above spends its budget on reasoning first (`glm-5.3` included: see the `Settings` docstring and
AE-0607), so no caller can take a small cap safely.

### What an empty answer does now

`generate` raises `EmptyLLMResponseError` on an answer with no visible text. On the queue this changes nothing,
because the queue already raises when every model is empty. On the routed model the primary already moved to the
fallback; the fallback's own empty answer is what now raises. The role-less model has no fallback, so it raises at
once.

| Caller | Before, on an empty answer | Now |
|---|---|---|
| Blog suggest | 200 with an empty suggestion, stored on the post | 500, nothing stored |
| Blog improve | 200 with empty `improved_text` | 500 |
| Blog translation | `BlogTranslationError` (the empty answer fails the JSON parse) | `BlogTranslationError` |
| Conversation title | Blank title saved | The service's first-message title |
| Refine image / design | `AllModelsUnavailableError` from the queue | Same |
| LinkedIn | `AllModelsUnavailableError` from the queue | Same |

The 500 is what those two routes already return for any other model failure: they map only `ValueError` to 400.

## Scope

- `generate` and `generate_stream` bind the temperature on the model.
- `max_tokens` removed from `LLMService` and the two protocols that restate it.
- `generate` raises `EmptyLLMResponseError` on an answer with no visible text.
- Both methods pass `get_langfuse_runnable_config()`.
- Trace context for the callers that had none: refine image and design, the conversation title, the LinkedIn
  generation name, and the agent name on `blog_ai_propagate`.

## Non-Goals

- No caller moves to another model or role (see Decision Log).
- No timeout, gate or threshold change. No new LLM call. No prompt change.
- `docs/backend/llm-model-routing.md` is not edited: PR #350 touches it.

## Acceptance Criteria

- [x] A request body test proves the requested temperature reaches the provider, on the role-less and fast models.
- [x] Every call keeps `max_completion_tokens: 32000`, and a caller cannot ask for less.
- [x] The caller audit table covers each caller's `max_tokens`, role and model.
- [x] An empty answer moves the call to the next model where there is one, and otherwise fails with a named error.
- [x] Each call is one Langfuse generation, with phase, agent and content type on its trace.
- [x] The tests stay hermetic: no exporter and no network.
- [x] The touched tests and the cheap backend gates pass.

## Gherkin Scenarios

`backend/tests/features/llm_service_params_ae0610.feature`

```gherkin
Feature: LLMService sends the requested temperature and records its calls (AE-0610)

  Scenario Outline: The provider receives the requested temperature
  Scenario: A caller that names no temperature sends the default
  Scenario: A streamed call receives the requested temperature
  Scenario: A caller cannot set a token cap
  Scenario: An empty answer moves the call down the fast queue
  Scenario: An empty answer moves the routed call to its fallback
  Scenario: An empty answer from the last routed model is a model failure
  Scenario Outline: An empty answer with no fallback is a model failure
  Scenario: The call reaches Langfuse as a generation
  Scenario: Without Langfuse the call runs with no callbacks
  Scenario Outline: A blog AI call is traced with its phase, agent and content type
  Scenario: A refined slide image prompt is traced
  Scenario: A refined carousel design is traced
  Scenario: A LinkedIn post is a named generation of the running phase
  Scenario: A conversation title is traced
```

## Delta

### ADDED

- Trace constants in `domain/constants/langfuse_tracing.py`; `_refinement_trace` in `carousel_refinement.py`.

### MODIFIED

- `AnthropicLLMService.generate` and `generate_stream`: temperature bound, traced; `generate` raises on empty.
- `blog_ai_propagate`: names the `blog_ai` agent (it defaulted to `editorial_workflow`).
- `LinkedInPostGenerator.generate`, `get_conversation_title_generator`: trace context.

### REMOVED

- `max_tokens` from `generate`, `generate_stream`, `LLMServiceProtocol` and `TranslationLLM`.
- `DEFAULT_TEMPERATURE` in `anthropic_llm.py`, which nothing else read.

## Affected Areas

- Backend: `infrastructure/external/anthropic_llm.py`, `domain/protocols/ai.py`, `domain/constants/langfuse_tracing.py`,
  `blog_post_ai_service.py`, `blog_translation_service.py`, `blog_workflow_observability.py`,
  `carousel_refinement.py`, `linkedin_post_generator.py`, `api/dependencies/conversation.py`
- Tests: new feature and two unit test files
- Observability: new generations for every `LLMService` call
- Frontend / Database / Deployment: none

## Dependencies

- Related: AE-0607 (reasoning uses up a small cap), AE-0609 (audit, PR #350, not merged)

## Implementation Plan

1. Audit the callers.
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

Audit done. Red before the fix: 15 of 19 new tests failed on the behaviour (`0.7 == 0.2`, `DID NOT RAISE`, no
generation, no trace), and 2 more failed on a bad test action, which was corrected. The other 2 pass by design: the
default temperature and the no-Langfuse path. Green after the fix.

## Files Touched

- See Affected Areas, plus `backend/tests/features/llm_service_params_ae0610.feature`,
  `backend/tests/unit/infrastructure/test_llm_service_params_ae0610.py`,
  `backend/tests/unit/application/test_llm_service_trace_scopes_ae0610.py`,
  `.agent/reports/AE-0610.dev-summary.md`

## Test Evidence

See `.agent/reports/AE-0610.dev-summary.md`. Full gate: lead's heavy slot. Mutation: CI only.

## QA Report

Pending.

## Decision Log

- **`max_tokens` removed, not honoured.** No caller uses it, and every model behind this service reasons out of the
  same budget, so there is no caller it would be safe for. Keeping an ignored argument hides the problem, and
  honouring it brings AE-0607 back the first time someone passes a small value. Removing it makes that a
  `TypeError`. A call that needs a cap can still `.bind` one on `chat_model`, as the drafter does.
- **Temperature bound on every call,** with no "only if not 0.7" check. The check saved nothing, and it assumed the
  model's default.
- **`bind`, not `with_config`.** It is what the drafter, the fit, cover ideas and palette use, and the kwargs reach
  each model of the queue and the fallback.
- **The role-less callers stay on the role-less model.** The ask was that an empty answer runs the fallback. For blog
  suggest, improve, translation and the title there is no fallback to run. Moving them to `fast_llm_service` would
  give them one, but it changes the model behind user-facing features, and `chat_model` for the blog persona path
  too. That is a routing decision, not part of a parameter fix, so it is the first follow-up. Here an empty answer
  fails with a named error instead of passing as a blank result.
- **`EmptyLLMResponseError` reused,** with no new type. It already names this failure on the routed model.
- **The empty check is in `generate`, not `generate_stream`.** The stream has no caller and yields chunks as they
  arrive.
- **`generate_stream` fixed, not deleted.** It had the same two lines. Deleting a protocol method is a separate change.
- **Title tracing at the DI edge.** `ConversationService` receives a plain callable and has no Langfuse dependency,
  so that stays the same.
- **LinkedIn uses `generation_run_name`, not a phase.** It runs inside the content phase, and a nested
  `propagate_attributes` would overwrite the phase metadata on the outer trace.
- **The temperature change is the visible effect.** Translation gets more literal (0.2), design more repeatable
  (0.3), LinkedIn looser (0.8). These are the values the code always asked for.

## Doc update after #350 merges

In `docs/backend/llm-model-routing.md`, replace the last sentence of the "Only four calls bind a cap" paragraph
(`LLMService.generate(max_tokens=...)` does not reach the provider either...) with:

> `LLMService.generate` has no `max_tokens` argument, so its callers always run at 32000. Its `temperature` is bound
> on the model and reaches the provider. An answer with no visible text raises `EmptyLLMResponseError`.

And add to the same section:

> Blog suggest, improve and translation and the conversation title use the role-less `container.llm_service()`, so
> they run on `GLM_MODEL` with no fallback and no per-call timeout. LinkedIn and the refine image / design tools use
> `fast_llm_service`. All `LLMService` calls are Langfuse generations.

In the AE-0609 audit table, blog AI suggest / improve / translation are `GLM_MODEL`, not fast.

## Follow-ups (not in this ticket)

- **Role-less callers have no fallback and no timeout.** `blog_post_ai.py:99`, `blog_editor.py:117` and
  `conversation.py` (`get_conversation_title_generator`) could use `fast_llm_service`. This is the owner's call. The
  routing doc records `glm-5.3` answering nothing after about 8.5 min, which is why it stopped being a fallback, and
  these calls still run on it.
- **Refinement's empty guards are now only reachable with a test double.** `_ERR_EMPTY_IMAGE_PROMPT` and
  `_ERR_EMPTY_CSS` stay, since the protocol does not promise the check.

## Blockers

None.

## Final Summary

`LLMService.generate` now sends the requested temperature, which changes translation, design refinement and
LinkedIn. `max_tokens` is gone, so every call keeps 32000. An empty answer is a named failure, after any fallback
has run. Every call is a Langfuse generation, with phase, agent and content type. Blog AI and the title still have no
fallback: moving them to the fast role is an open decision.
