# AE-0285 — backend llm provider toggle: glm 5.2 via opencode go (replace sonnet for carousel and chat agents)

Status: Intake
Tier: T2
Priority: P2
Type: Feature
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-25
Updated: 2026-06-25

## Goal

Make the backend chat LLM **provider-configurable** so carousel generation, the
alter-ego chat agent, and the RAG agent can run on **GLM 5.2 (via the OpenCode Go
OpenAI-compatible endpoint)** instead of Claude Sonnet — cutting Anthropic spend —
with Anthropic kept as a toggleable fallback for A/B and rollback.

## Problem

(User goal: reduce Anthropic API cost.) Every chat-LLM call in the backend is
hardwired to Claude Sonnet via `settings.anthropic_model = "claude-sonnet-4-6"`,
constructed as `ChatAnthropic` at **3 points**:
1. `infrastructure/external/anthropic_llm.py` (`AnthropicLLMService`, wired in
   `container.py`) → `.chat_model`, consumed by the **carousel content nodes,
   editorial workflow, personas, rubrics, sources, blog-post AI, LinkedIn
   generator, PersonaAgent** — the whole carousel brain.
2. `agents/alter_ego_agent.py` — inline `ChatAnthropic` for the alter-ego chat
   DeepAgent.
3. `agents/rag_agent.py` — inline `ChatAnthropic` for the RAG DeepAgent.

Everything downstream only sees a LangChain `BaseChatModel`, so the provider can
be swapped behind a factory with zero downstream change. GLM 5.2 is
OpenAI-compatible (`langchain_openai.ChatOpenAI`, also a `BaseChatModel`).

## Scope

- **Settings** (`infrastructure/config/settings.py`): add `llm_provider`
  (`"anthropic" | "glm"`, default `"glm"`), `glm_api_key: SecretStr`,
  `glm_base_url` (default `https://opencode.ai/zen/go/v1`), `glm_model`
  (default `glm-5-2`).
- **Factory** (`infrastructure/external/chat_model_factory.py`, new):
  `build_chat_model(settings) -> BaseChatModel` — GLM `ChatOpenAI(base_url, model,
  api_key)` when `llm_provider="glm"` **and a GLM key is present**, else
  `ChatAnthropic` (same temperature/streaming/max_tokens/retries). The "glm but no
  key → Anthropic + warning" fallback keeps CI and a not-yet-configured prod safe.
- **Rewire the 3 instantiation points** through the factory (the service +
  the two inline agents share one path); `chat_model` return type → `BaseChatModel`.
- Tests for the factory (each provider + the no-key fallback); a `.feature`.
- Local `.env`: `LLM_PROVIDER=glm` + `GLM_API_KEY=…` (OpenCode Go key) for the
  E2E carousel validation.

## Non-Goals

- Image generation (DALL-E/gpt-image) and quality scoring (gpt-4o-mini) are
  unaffected — only the Sonnet chat/orchestration calls move.
- Not removing Anthropic (kept as the toggle/fallback).
- No prompt re-tuning for GLM in this ticket (flagged as a follow-up if quality
  needs it).

## Acceptance Criteria

- [ ] `llm_provider=glm` + a GLM key routes all 3 chat-LLM construction points to
      `ChatOpenAI(base_url=glm_base_url, model=glm_model)`; `llm_provider=anthropic`
      (or glm without a key) routes to `ChatAnthropic`.
- [ ] No downstream consumer changes (all still receive a `BaseChatModel`).
- [ ] `build_chat_model` is unit-tested for anthropic, glm, and glm-no-key
      fallback; `.feature` added.
- [ ] `bash scripts/ci/gates.sh backend` green (mypy strict, ruff, tests,
      arch-ratchet, integrity, …).
- [ ] **Validated end-to-end**: a real carousel generated locally on GLM 5.2
      (DeepAgents tool-calling + streaming confirmed working over the
      OpenAI-compatible endpoint).

## Gherkin Scenarios

```gherkin
Feature: Configurable backend chat LLM provider

  Scenario: GLM provider selected with a key
    Given llm_provider is "glm" and a GLM api key is set
    When the chat model is built
    Then it is an OpenAI-compatible client pointed at the GLM base_url and model

  Scenario: Anthropic provider selected
    Given llm_provider is "anthropic"
    When the chat model is built
    Then it is a ChatAnthropic using the configured Claude model

  Scenario: GLM selected but no key (CI / prod not yet configured)
    Given llm_provider is "glm" and the GLM api key is empty
    When the chat model is built
    Then it falls back to ChatAnthropic and logs a warning
```

## Delta

### ADDED

- `infrastructure/external/chat_model_factory.py` + its unit test
- settings: `llm_provider`, `glm_api_key`, `glm_base_url`, `glm_model`
- `.feature`

### MODIFIED

- `infrastructure/external/anthropic_llm.py` (use factory; return `BaseChatModel`)
- `agents/rag_agent.py`, `agents/alter_ego_agent.py` (use factory)
- `.env.example` / docs noting the GLM env vars

### REMOVED

- the 3 hardcoded `ChatAnthropic(...)` constructions (now via the factory)

## Affected Areas

- Backend: the chat-LLM construction layer (factory + 3 call sites)
- Frontend: none
- Database: none
- API: none (same `BaseChatModel` contract)
- Tests: factory unit tests + `.feature`
- Docs: env var documentation
- Prompts/LLM: provider swap (no prompt changes)
- Observability: Langfuse callbacks unchanged (model name will reflect GLM)
- Deployment: ⚠️ prod must add `GLM_API_KEY` (+ `LLM_PROVIDER=glm`) as GitHub
  Secrets before merge, or prod keeps using Anthropic via the no-key fallback.

## Dependencies

- Blocks:
- Blocked by:
- Related: OpenCode Go docs (https://opencode.ai/docs/go/),
  `[[external-review-opencode-go-route]]`, ADR-0007 (carousel pipeline).

## Implementation Plan

1. settings: add the 4 fields.
2. `chat_model_factory.build_chat_model()` (provider switch + no-key fallback).
3. Rewire `anthropic_llm.py` + `rag_agent.py` + `alter_ego_agent.py`.
4. Unit tests + `.feature`; `gates.sh backend`.
5. Local `.env` GLM creds → drive a full carousel via Playwright (the E2E test)
   to validate tool-calling/streaming on GLM 5.2.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-25 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
