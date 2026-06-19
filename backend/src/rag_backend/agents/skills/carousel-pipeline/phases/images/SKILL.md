---
name: carousel-pipeline-images
description: Image generation phase of the editorial carousel workflow. Render intro and content slide images via Gemini before human review.
version: 2.0.0
---

# Images Phase

## Shared standards (read first)

- [`../_shared/image-generation.md`](../_shared/image-generation.md) — scene-only prompts, Gemini wrapper, slide scope, rate limiting
- [`../_shared/anti-patterns.md`](../_shared/anti-patterns.md) — speech bubbles, missing intro hero, style in LLM prompt

## Purpose

Generate images for intro + content slides (1-4) using `ImageGenerationTool` (Gemini `gemini-3.1-flash-image-preview`). Runs at **phase enter** via `generate_carousel_images` — not on design approval in the resume handler.

Rendered slide images must exist **before** `phase_status: awaiting_human`.

## Generation scope

| Slides | Image |
|--------|-------|
| 1 (intro) | Hero image — **required** |
| 2-4 (content) | Supporting visuals |
| 5 (closing) | No image (checklist layout) |
| 6 (cta) | No image (save/share buttons) |

## Prompt rules

The LLM's `image_prompt` is scene description only. Server wraps with mandatory style directives via `_build_gemini_prompt`. See [`image-generation.md`](../_shared/image-generation.md) for the full wrapper template.

- 2-3 second delay between API calls (rate limiting)
- Save to `{output_dir}/images/slide_{n}.jpg`
- HTML references relative paths resolved during Playwright export

## Editorial HITL gate

**Artifacts shown at review:**

- Rendered slide images (authenticated preview URLs)
- Generation metadata (provider, prompt summary)
- Failed slide indicators

**Human actions via `POST /workflow/resume`:**

- **Approve** — advance to final review; blog composition and quality scoring start on final-review phase enter
- **Revise** — per-slide regeneration instructions; re-invokes `render_images` for selected slides only

**Phase lifecycle:** `in_progress` → generate → `awaiting_human` → approve or revise (loop, max 5 revisions) → next phase.

## Python execution

Deterministic node: `render_images` → `generate_carousel_images`, `run_images`

Requires `GEMINI_API_KEY`. Langfuse metadata: `project_id`, `phase=images`, `agent_name=render_images`, `content_type=carousel`
