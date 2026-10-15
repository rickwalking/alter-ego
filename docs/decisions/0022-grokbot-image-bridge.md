---
status: proposed
date: 2026-10-15
decision-makers: Pedro Marins
consulted: Claude (codex image spike, AE-0393 design)
informed: delivery team
---

# ADR-0022: Generate carousel images through the Grok Bot via an async, OpenAI-compatible bridge

## Context and Problem Statement

The carousel `images` phase pays per image through the OpenAI Images API (`gpt-image-2`).
The owner already pays for subscriptions whose agents can generate images: a 2026-10-15 spike on
the prod VPS showed the Codex CLI generating usable slide images (~50 s each, ~1122×1402 PNG). The
owner prefers to run image generation on the **Grok Bot** (Cursor subscription), which can be
triggered by a webhook and can call our API back.

How do we route image generation to an asynchronous, external agent without touching the
workflow, and without losing reliability?

## Decision Drivers

- Zero new subscriptions; cut the per-image API cost.
- No change to prompts, style strategies, the workflow graph or the autopilot gates.
- Must never make a carousel fail where OpenAI would have succeeded.
- Agent jobs are slow (≈1 min) and asynchronous; the backend runs several uvicorn workers.
- The prod VPS has little free RAM, so nothing heavy runs on it.

## Considered Options

1. **Async webhook + callback bridge behind the existing `ImageGenerationService` port**, with
   the OpenAI service as the fallback.
2. Run the Codex CLI on the VPS behind a local OpenAI-compatible HTTP shim.
3. A synchronous HTTP proxy that the OpenAI SDK calls via `base_url`.

## Decision Outcome

Chosen: **option 1**. Design and contract: [GrokBot Image Bridge](../architecture/grokbot-image-bridge.md).

- The webhook carries the request (prompt, size, one-time callback token). The Grok Bot replies
  to `POST /api/v1/image-bridge/jobs/{id}/result` with an **OpenAI `ImagesResponse`** (`b64_json`)
  or an OpenAI error body.
- The waiter polls Postgres, so it works across workers. It normalizes the image to the
  requested size and writes it to the same path the OpenAI service would.
- A flag (`IMAGE_BRIDGE_ENABLED`, default off) controls it, and every failure falls back to OpenAI.

### Consequences

- Good: no new spend per image; the workflow is unaware of the provider; instant rollback with
  the flag.
- Good: no agent process or extra RAM on the prod VPS; the work runs on the Grok Bot side.
- Bad: images take ~1 min each instead of seconds. That is acceptable for the autopilot, and the
  concurrency cap is 2.
- Bad: output quality, size and refusals depend on an agent, not a contract. Normalization and the
  fallback contain this.
- Risk: the provider's terms for automated use of a subscription are not settled. The owner
  accepts the risk; the flag and fallback make it reversible.

### Why not option 2

Codex on the VPS works (spike) but needs ~320 MB per job on a host already using swap, and keeps
a ChatGPT login on prod. It remains a possible second primary provider behind the same port.

### Why not option 3

The OpenAI SDK call is synchronous and would hold an HTTP request open for ~1 min per image
through nginx with no retry semantics. Implementing the port directly is simpler and keeps the
fallback in-process.
