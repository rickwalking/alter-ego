# opencode Zen "Go" endpoint — DeepSeek for the carousel agent

Companion to `carousel-deepseek-feasibility.md`. Resolves the open "is there a hosted
endpoint" question. **Source: opencode Zen "Go" model table, provided by the user
(2026-06-18).** Confirm against live opencode.ai docs at implementation time (model IDs
+ tool-calling support move fast).

## Confirmed facts (from the provided docs)

opencode Zen **"Go"** plan exposes hosted, SDK-callable endpoints (NOT the CLI):

| Surface | Endpoint | SDK shape |
|---------|----------|-----------|
| OpenAI-compatible | `https://opencode.ai/zen/go/v1/chat/completions` | `@ai-sdk/openai-compatible` |
| Anthropic-compatible | `https://opencode.ai/zen/go/v1/messages` | `@ai-sdk/anthropic` |

**DeepSeek models (OpenAI-compatible surface):**
- `deepseek-v4-pro` — DeepSeek V4 Pro
- `deepseek-v4-flash` — DeepSeek V4 Flash (cheap/fast tier)

Other Go models: `glm-5.2/5.1`, `kimi-k2.7/k2.6`, `mimo-v2.5(-pro)` (OpenAI-compatible);
`minimax-m3/m2.7/m2.5`, `qwen3.7-max/plus`, `qwen3.6-plus` (Anthropic-compatible).

## LangChain / DeepAgents wiring (the OpenAI-compatible path)

The DeepSeek V4 models use the `chat/completions` surface → drive them with `ChatOpenAI`
pointed at the Zen base URL (LangChain appends `/chat/completions`):

```python
from langchain_openai import ChatOpenAI

deepseek = ChatOpenAI(
    base_url="https://opencode.ai/zen/go/v1",     # NOT the full /chat/completions path
    api_key=settings.OPENCODE_ZEN_API_KEY,         # the Go-plan key, via Pydantic Settings + GH Secret
    model="deepseek-v4-flash",                     # research/extraction; v4-pro for scoring
    # temperature etc. per phase
).with_fallbacks([claude_sonnet])                  # voice/uptime safety net
```

- This slots into the single carousel model seam the architect found
  (`carousel_editorial_orchestrator.py:42-52` ← `container.llm_service().chat_model`).
- Inject `deepseek-v4-flash` into `SourceSynthesisAgent` (research/extraction) and
  optionally `deepseek-v4-pro` into `QualityAgent` (scoring); **keep Claude Sonnet** on
  `ContentDraftAgent` / caption / persona enforce+gate (the voice surface).
- Langfuse tracing is unaffected — the LangChain callback works with any `ChatOpenAI`
  regardless of `base_url`; add a `model_provider="opencode-zen"` tag for cost attribution.

## To VERIFY at implementation (do not assume)
1. **Tool-calling + JSON/structured-output** for `deepseek-v4-*` THROUGH the Zen gateway —
   the carousel subagents rely on it. If the gateway strips/limits function-calling, the
   structured phases break → fall back to Claude for those calls.
2. **ToS / acceptable use** — confirm the Go-plan key is licensed for programmatic SDK use
   (the docs presenting these as "API endpoints" strongly implies yes; confirm quotas).
3. **Token/usage accounting + rate limits + SLA** of the Zen gateway vs DeepSeek's own API.
4. **Data residency** (DeepSeek/PRC) governance for any user content sent.
5. Live **model IDs** (`deepseek-v4-pro/flash`) — these are post-cutoff; re-check the table.

## Recommendation
Use the **opencode Zen Go endpoint** (single subscription key, included models) as the
DeepSeek source for the pilot, via `ChatOpenAI(base_url=...)` + `.with_fallbacks([claude])`.
Keep **DeepSeek's direct API** (`https://api.deepseek.com`) as the documented fallback
provider if Zen ToS/quotas/SLA prove unsuitable. Lands as **ADR-019 (tiered model
selection)**, piloted on `SourceSynthesisAgent` after P1, wired via the P3 harness config.
