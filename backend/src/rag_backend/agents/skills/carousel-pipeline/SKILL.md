---
name: carousel-pipeline
description: Route carousel creation to the editorial workflow and phase subagents. Use when the user says "create a carousel", "create a new social media post", "generate carousel slides", "make an Instagram post", "start editorial workflow", or "create blog content". Never use for plain text generation without visual content or for refining an existing carousel (use carousel-refinement).
version: 2.0.0
---

# Carousel Pipeline

## Purpose

Generate production-ready Instagram carousel content through the **editorial workflow**: research → outline → content → design → images → final review, with human approval gates at each phase.

Produces bilingual blog posts (pt-BR + en), design tokens, slide images, and Instagram caption.

## Prerequisites

See [`_shared/critical-rules.md`](_shared/critical-rules.md#prerequisites).

## How to run

1. Create a carousel project: `POST /api/carousels`
2. Start editorial workflow: `POST /api/carousels/{id}/workflow/start`
3. Monitor progress: `GET /api/carousels/{id}/workflow/stream` (SSE)
4. Human decisions: `POST /api/carousels/{id}/workflow/resume` (approve or revise)

Do **not** use legacy `/generate` or `/stream` endpoints — removed in consolidation.

## Route by content mode (AE-0375, ADR-0021)

The project's `content_mode` and stamped contract pick the prompts:

| Mode | Contract | Outline / content prompts | Notes |
|------|----------|---------------------------|-------|
| `news_analysis` (Radar IA, default) | `hero_lower_third_v4` (new) or v1-v3 (existing) | `carousel/v3` outline + `carousel/v6` content (`carousel/v7` from AE-0376) | ≤1 "what happened" slide, ≥3 "what it changes for you", closing = the owner's verdict. |
| `pov` (Ponto de Vista) | `pov_hook_v1` (8-10 slides) | `carousel_pov/v1/{hook,outline,content,caption}` | From the owner's thesis; 5 hook candidates on outline slide 1, picked at the outline gate. |

Roles (`hook`, `rehook`, `pov`, `point`, `twist`, `save`, `cta`; Radar IA v4: `news`, `impact`,
`verdict`) are stamped on the outline by position from the contract, never taken from the model.
The model may sharpen the owner's thesis but never invent their opinion, experiences, test results
or numbers.

## Delegate to phase subagents

Do not load the full workflow into parent agent context. Route work via `task` to the phase subagent for the current workflow phase:

| Phase | Subagent / node | Phase skill |
|-------|-----------------|-------------|
| Research | `research_synthesizer` | [`phases/research/SKILL.md`](phases/research/SKILL.md) |
| Outline | `outline_planner` | [`phases/outline/SKILL.md`](phases/outline/SKILL.md) |
| Content | `content_drafter` | [`phases/content/SKILL.md`](phases/content/SKILL.md) |
| Design | `apply_design` | [`phases/design/SKILL.md`](phases/design/SKILL.md) |
| Images | `render_images` | [`phases/images/SKILL.md`](phases/images/SKILL.md) |
| Final review | `compose_blog`, `score_quality`, caption | [`phases/final-review/SKILL.md`](phases/final-review/SKILL.md) |

Each phase skill references only the `_shared/` files it needs — see [`_shared/README.md`](_shared/README.md).

## Shared standards

All content contracts, anti-patterns, design tokens, and formatting rules live in [`_shared/`](_shared/):

- [`critical-rules.md`](_shared/critical-rules.md)
- [`anti-patterns.md`](_shared/anti-patterns.md)
- [`content-contracts.md`](_shared/content-contracts.md)
- [`text-formatting.md`](_shared/text-formatting.md)
- [`design-system.md`](_shared/design-system.md)
- [`image-generation.md`](_shared/image-generation.md)
- [`export-and-caption.md`](_shared/export-and-caption.md)

## Refinement

To tweak an existing carousel without full re-generation, use [`../carousel-refinement/SKILL.md`](../carousel-refinement/SKILL.md).

## Related

- Legacy `workflow.md` is deprecated — content migrated to `_shared/` + `phases/`
- [Carousel Pipeline Consolidation Plan](../../docs/plans/carousel-pipeline-consolidation.md)
