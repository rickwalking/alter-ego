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
| JSON repair, `extract_json_with_repair` (`json_utils.py:105`) | no caller in `src` today | whichever `llm` it is given | 0.2 | none | not reached | 0.2 / 32000 if a caller appears | Depends on the `llm` |
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
| Refine image / design | `AllModelsUnavailableError` from the queue | Same, with a queue. See below |
| LinkedIn | `AllModelsUnavailableError` from the queue | Same, with a queue. See below |

The 500 is what those two routes already return for any other model failure: they map only `ValueError` to 400.

"Same" holds only when `LLM_MODEL_QUEUE_FAST` is set. `deploy.yml:173` sets it by default, so production has a queue.
Without one, the fast role is a routed model with a fallback, and a blank answer from that fallback now raises
`EmptyLLMResponseError`:

- **LinkedIn:** before, the blank post was stored. Now the error leaves `build_editorial_distribution_updates`, which
  has no handler around `generate_both`, and the content phase fails.
- **Refine image / design:** before, the tool answered that it could not apply the change. Now it answers
  `ERR_CAROUSEL_TOOL_UNEXPECTED`. Nothing is changed in either case.

## Scope

- `generate` and `generate_stream` bind the temperature on the model.
- `max_tokens` removed from `LLMService` and the two protocols that restate it.
- `generate` raises `EmptyLLMResponseError` on an answer with no visible text.
- Both methods pass `get_langfuse_runnable_config()`.
- `LlmCallTrace`, a domain value on the `LLMService.generate` port: a caller with no phase around it names its phase,
  agent and content type, and the adapter opens the trace. Refine image and design and the conversation title use it.
- `blog_ai_propagate` names the `blog_ai` agent.
- Traces carry the user where one is known: refine image and design, the conversation title, and blog suggest, improve,
  section rewrite and the translation route. The conversation title also carries the conversation id as its project id.

## Non-Goals

- No caller moves to another model or role (see Decision Log).
- No timeout, gate or threshold change. No new LLM call. No prompt change.
- The temperatures callers request stay as they are.
- `EmptyLLMResponseError` on the blog suggest and improve routes stays a generic 500.

## Acceptance Criteria

- [x] A request body test proves the requested temperature reaches the provider, on the role-less and fast models.
- [x] Every call keeps `max_completion_tokens: 32000`, and a caller cannot ask for less.
- [x] The caller audit table covers each caller's `max_tokens`, role and model.
- [x] An empty answer moves the call to the next model where there is one, and otherwise fails with a named error.
- [x] Each call is one Langfuse generation, with phase, agent and content type on its trace.
- [x] Refinement, conversation title and blog AI traces carry the user id where one is known, and the explicit
  `unknown` fallback where none is.
- [x] The conversation title trace carries the conversation id as its project id.
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
  Scenario Outline: A blog AI call records the user who asked for it
  Scenario: A blog translation with no user keeps the unknown fallback
  Scenario Outline: A refinement names its own phase
  Scenario: A refinement of a project with no owner names no user
  Scenario: A conversation title names its own phase
  Scenario: The service opens the phase the call names
  Scenario: A call that names no user keeps the unknown fallback
  Scenario: A failing call closes the phase it named
```

## Delta

### ADDED

- `LlmCallTrace` in `domain/protocols/ai.py`; the `trace` argument of `LLMService.generate`.
- Trace constants in `domain/constants/langfuse_tracing.py`.

### MODIFIED

- `AnthropicLLMService.generate` and `generate_stream`: temperature bound, traced; `generate` raises on empty.
- `blog_ai_propagate`: names the `blog_ai` agent (it defaulted to `editorial_workflow`).
- `regenerate_slide_image`, `refine_carousel_design`, `get_conversation_title_generator`: pass an `LlmCallTrace`.
- `LlmCallTrace` gains `user_id`. `get_conversation_title_generator` takes the conversation id and the signed-in user.
- `blog_ai_propagate` takes an optional `user_id`, and `BlogTranslationService.translate` an optional `user_id`.
- `docs/backend/llm-model-routing.md`: the `LLMService` paragraph. AE-0609 ticket: the blog AI audit row.

### REMOVED

- `max_tokens` from `generate`, `generate_stream`, `LLMServiceProtocol` and `TranslationLLM`.
- `DEFAULT_TEMPERATURE` in `anthropic_llm.py`, which nothing else read.
- The two `if not ...: raise ValueError` empty guards in `carousel_refinement.py`, their constants and their two tests.

## Affected Areas

- Backend: `infrastructure/external/anthropic_llm.py`, `domain/protocols/ai.py`, `domain/constants/langfuse_tracing.py`,
  `domain/protocols/__init__.py`, `blog_post_ai_service.py`, `blog_translation_service.py`,
  `blog_workflow_observability.py`,
  `carousel_refinement.py`, `api/dependencies/conversation.py`, `api/routes/blog_post_sections.py`
- Tests: new feature and two unit test files
- Observability: new generations for every `LLMService` call
- Frontend / Database / Deployment: none

## Dependencies

- Related: AE-0607 (reasoning uses up a small cap), AE-0609 (audit, PR #350, merged)

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

Audit done. Red before the fix: 15 of the first 19 new tests failed on the behaviour (`0.7 == 0.2`, `DID NOT RAISE`,
no generation, no trace), and 2 more failed on a bad test action, which was corrected. The other 2 pass by design:
the default temperature and the no-Langfuse path.

The first version opened the phases in the callers. `backend:imports`, `backend:arch-ratchet` and `backend:integrity`
failed on it: three new application/API imports of infrastructure. Those are real layering violations, and the
baseline is not grown for them, so the trace moved onto the port as a domain value and the imports went away. The
LinkedIn scenario went with them (see Decision Log). The tests were rewritten to match, then green.

Review round 1 follow-ups. Against the old source, keeping only the new `LlmCallTrace.user_id` field so the tests
collect, 14 tests failed on the behaviour: no user id on the refinement, title and blog traces, and the exact
`blog_ai_propagate` arguments. Two new tests pass by design there: the `unknown` fallback and the project with no owner.

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
- **`LlmCallTrace` on the port, not `propagate_attributes` in the callers.** The application layer and the API may not
  import Langfuse, and new import pairs would grow the baseline. A domain value keeps them clean, and it follows the
  way the palette service gets its trace from outside. It replaces `max_tokens` in the argument list, so the
  signature stays at the same size. `LLMServiceProtocol` and `TranslationLLM` keep their shorter shape, since their
  callers trace through `blog_ai_propagate`.
- **Title trace at the DI edge.** `ConversationService` receives a plain callable, and `partial` keeps it plain.
- **LinkedIn is unchanged.** It runs inside the content phase, so its generation already gets that phase's metadata
  from `generate`, the same as the caption. A nested phase would overwrite the phase on the outer trace. Its
  generation is named `carousel.content`, like the caption.
- **The refinement's user is the project owner.** Both agent tools run `load_authorized_project`, which refuses anyone
  but the owner, so the owner is the caller. The project is already loaded there, so the `CarouselRefinementService`
  port keeps its signature. A project with no owner records `unknown`.
- **The conversation id goes in the title trace's project field.** It groups the title with its conversation and fills
  a required field. `get_conversation_title_generator` reads both values through FastAPI, and the route keeps its
  ownership check.
- **`blog_ai_propagate` keeps `post_id` as metadata.** The user id was the ask. Its traces still record
  `project_id=unknown`, which is a follow-up.
- **Only the translation route passes a user.** `BlogDocumentTranslator` keeps its two arguments, because its callers,
  the EN gate and the EN repair, are background work with no user.
- **The blog image call is unchanged.** It goes to an image provider, not through `LLMService`.
- **The refinement's empty guards are removed.** `generate` raises first, so they could only run with a test double.
- **The temperature change is the visible effect.** Translation gets more literal (0.2), design more repeatable
  (0.3), LinkedIn looser (0.8). These are the values the code always asked for.

## Follow-ups (not in this ticket)

- **Role-less callers have no fallback and no timeout.** `blog_post_ai.py:99`, `blog_editor.py:117` and
  `conversation.py` (`get_conversation_title_generator`) could use `fast_llm_service`. This is the owner's call. The
  routing doc records `glm-5.3` answering nothing after about 8.5 min, which is why it stopped being a fallback, and
  these calls still run on it.
- **Blog AI traces record `project_id=unknown`.** `blog_ai_propagate` sends the post id as `post_id` only.

## Blockers

None.

## Final Summary

`LLMService.generate` now sends the requested temperature, which changes translation, design refinement and
LinkedIn. `max_tokens` is gone, so every call keeps 32000. An empty answer is a named failure, after any fallback
has run. Every call is a Langfuse generation, with phase, agent and content type, and with the user id where one is known.
Blog AI and the title still have no fallback: moving them to the fast role is an open decision.
