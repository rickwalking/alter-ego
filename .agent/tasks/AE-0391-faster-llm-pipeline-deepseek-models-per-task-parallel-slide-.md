# AE-0391 — Faster LLM pipeline: DeepSeek models per task, parallel slide drafting, GLM fallback

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0391-deepseek-parallel
Created: 2026-10-15
Updated: 2026-10-15

## Goal

Cut the carousel content phase from 60+ min to minutes: route each LLM task to a fast DeepSeek
model on the OpenCode Go endpoint, draft slides in parallel, and fall back to GLM-5.3 on failure.

## Problem

Every carousel LLM call ran on `glm-5.3` (a reasoning model) via `llm_provider="glm"`. A content
phase made ~15 sequential calls of 3-10 min each, so content alone took 60+ min (Langfuse: 27k
input → 128k output tokens). Benchmarks on the same endpoint/key (2026-10-15): single-slide JSON
80.6 s on glm-5.3 vs 16.6 s on deepseek-v4-pro and 14-18 s on deepseek-v4.1-flash; 7-slide
outline 76.6 s vs 40.4 s / 22.8 s. All valid JSON, correct casing, no invented numbers.

## Scope

- Per-task routing via settings: `LLM_MODEL_REASONING` (deepseek-v4-pro), `LLM_MODEL_FAST`
  (deepseek-v4.1-flash), `LLM_MODEL_FALLBACK` (glm-5.3); defaults in constants; per-call timeouts
  240 s / 120 s; same endpoint/key/session header; `build_chat_model(settings, role)`.
- Automatic fallback on 5xx / non-auth 4xx / timeout / empty content / bad JSON after
  `llm_json_retry`, with a structured warning and a `fallback:true` Langfuse tag.
- Parallel slide drafting (`CONTENT_DRAFT_CONCURRENCY`, default 4), outline-order output,
  outline-only sibling context; persona scoring uses the same bound.
- Langfuse: each generation records the actual model and `role:<role>`.
- Env in `deploy.yml` + `docker-compose.prod.yml`; docs + root model table.

## Non-Goals

- Do not refactor unrelated code
- No change to chat / RAG agents (single `GLM_MODEL`), nor to the Anthropic provider semantics
- No DB migration; no tracing rework (AE-0390 lives on its own branch)

## Acceptance Criteria

- [x] Reasoning role (research synthesis, outline, rubric judgement) runs `LLM_MODEL_REASONING`
- [x] Fast role (drafting, translation, caption/LinkedIn/blog copy, refinement, AE-0367 autofix
  re-translate, persona scoring) runs `LLM_MODEL_FAST`
- [x] Fallback model answers on error / timeout / empty / bad JSON; auth errors are re-raised
- [x] Each fallback logs `llm_fallback_used` / `llm_json_fallback_used` and tags `fallback:true`
- [x] Slides drafted concurrently, max `CONTENT_DRAFT_CONCURRENCY` in flight, outline order kept
- [x] One failing slide is retried alone, then sent to the fallback; siblings drafted once
- [x] Anthropic provider / no-key semantics unchanged; no hard-coded model ids outside constants
- [x] Settings in `deploy.yml` and `docker-compose.prod.yml` with defaults
- [x] Gherkin: `backend/tests/features/llm_model_routing_ae0391.feature`
- [x] Docs: `docs/backend/llm-model-routing.md`, backend + root `CLAUDE.md`

## Repro Steps

1. Start a carousel in prod; watch the content phase in Langfuse.
2. Before: ~15 sequential glm-5.3 generations, 3-10 min each.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None. (DeepSeek needs the owner's OpenCode "Global regions" setting — already ON.)

## Progress Log

### 2026-10-15

Ticket created (hotfix fast path). Implemented routing, fallback, parallel drafting, tests, docs.

## Files Touched

See `.agent/reports/AE-0391.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0391.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
