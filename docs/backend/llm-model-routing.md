# LLM model routing (AE-0391)

Carousel LLM calls go to a model chosen **per task role**. All models are served
by the OpenCode Go OpenAI-compatible endpoint (`GLM_BASE_URL`, default
`https://opencode.ai/zen/go/v1`) with the same key (`GLM_API_KEY`) and the
`x-opencode-session` header (AE-0330).

| Role | Setting (env) | Default | Per-call timeout | Used for |
|---|---|---|---|---|
| reasoning | `LLM_MODEL_REASONING` | `deepseek-v4-pro` | 240 s | research synthesis, outline, quality/rubric judgement |
| fast | `LLM_MODEL_FAST` | `deepseek-v4.1-flash` | 120 s | slide drafting (+ persona enforce), PT→EN translation, caption, LinkedIn/blog distribution copy, refinement, AE-0367 autofix re-translate, persona scoring |
| fast fallback | `LLM_MODEL_FALLBACK` | `qwen3.8-flash` | 180 s | a fast call that failed 5 attempts |
| reasoning fallback | `LLM_MODEL_FALLBACK_REASONING` | `qwen3.8-max` | 180 s | a reasoning call that failed 5 attempts |

**Retries (AE-0395).** Every model gets 5 attempts (`LLM_ATTEMPTS_PER_MODEL`) for a timeout,
an error (except 401/403) or empty content, with backoff 2 s, 4 s, 8 s, 15 s (`llm_retry` log),
before the call moves to the role's fallback, which gets 5 attempts too. A JSON call
(`agents/llm_json_retry.py`) also gets 5 attempts (each with its re-roll and repair) per model
(`llm_json_retry` log). GLM-5.3 is no longer a fallback: in prod on 2026-10-16 it returned empty
content after ~8.5 min, four times in a row. Fallback benchmark (prod endpoint, 2026-10-16, a
pt-BR caption as strict JSON, 2 runs): `qwen3.8-flash` 9-11 s, `qwen3.8-max` 14-24 s,
`mimo-v2.6-flash` 7-19 s, `kimi-k2.6` 44-47 s, all valid JSON. `claude-haiku-5-5`,
`gpt-5.6-luna`, `minimax-m2.7` and `grok-4.6` answer `ModelProtocolUnsupported` on this endpoint.

Model ids live only in settings; the defaults are constants in
`backend/src/rag_backend/infrastructure/config/llm_routing_constants.py`.

## How it works

- `chat_model_factory.build_chat_model(settings, role)` returns a
  `RoutedChatModel` (`infrastructure/external/routed_chat_model.py`) wrapping
  the role's model and the fallback model. `build_role_models(settings)` builds
  both roles; `AnthropicLLMService.role_models` caches them.
- Without a role (chat / RAG agents) the single `GLM_MODEL` is built, as before.
- `LLM_PROVIDER=anthropic`, or `glm` without a key, returns the configured
  Anthropic model for every role, as before (AE-0285).

### Fallback

The fallback model re-runs the same call when the primary:

- raises any error except auth (`401`/`403` re-raise: the fallback uses the same
  key) — this covers 5xx, other 4xx, and `429` once the OpenAI SDK's own retries
  (exponential backoff honouring `Retry-After`, `max_retries=3`) are spent;
- exceeds its per-call timeout;
- returns empty content (and no tool call);
- returns JSON that still does not parse after the `llm_json_retry` re-roll and
  repair (the whole retry policy runs once more on the fallback).

Each use logs a structured warning (`llm_fallback_used` /
`llm_json_fallback_used`, with `role`, models and `reason`).

### Langfuse

The wrapper adds no generation of its own: the inner model's run is the
generation, so token usage is counted once and the **actual** model name is
recorded. Each run carries the tags `role:<reasoning|fast>` and `model:<id>`,
plus `fallback:true` when the fallback ran, and the same data as metadata
(`llm_role`, `llm_model`, `llm_fallback`).

## Parallel slide drafting

The content phase drafts all slides concurrently behind a semaphore
(`CONTENT_DRAFT_CONCURRENCY`, default 4). Results keep outline order. Each
draft sees only its siblings' **outline** titles/key points (never a sibling's
fresh draft); the existing distinctness check re-drafts near-duplicates after.
A failing slide is retried on its own (re-roll / repair, then the fallback); if
it still fails, the phase fails once every sibling has settled. Persona scoring
of the drafts uses the same bound. EN translation is a single batched call.

## Benchmarks (prod endpoint, 2026-10-15)

Before: every call ran on `glm-5.3`, a reasoning model. A content phase made ~15
sequential calls of 3-10 min each (60+ min; Langfuse: 27k input → 128k output
tokens).

| Task | glm-5.3 | deepseek-v4-pro | deepseek-v4.1-flash | glm-5.3-flash |
|---|---|---|---|---|
| Single-slide JSON | 80.6 s / 5.6k out | 16.6 s / 1.4k | 14–18 s / 2.2–2.5k | 3–4 s / 0.2k |
| 7-slide outline | 76.6 s / 5.0k out | 40.4 s / 3.3k | 22.8 s / 3.3k | 42.9 s / 2.8k (titles too long) |

All produced valid JSON and correct casing, and none invented numbers. The
DeepSeek outlines had the best builder POV. DeepSeek requires the account's
"Global regions" setting (on).
