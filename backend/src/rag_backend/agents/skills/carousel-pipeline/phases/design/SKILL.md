---
name: carousel-pipeline-design
description: Design system phase of the editorial carousel workflow. Apply theme tokens and HTML carousel layout before human review.
version: 2.0.0
---

# Design Phase

## Shared standards (read first)

- [`../_shared/design-system.md`](../_shared/design-system.md) — theme resolution, token schema, typography, feature-grid CSS, intro footer flex

## Purpose

Generate design tokens and build self-contained HTML carousel using the resolved palette. Runs at **phase enter** via `apply_design_tokens` + `run_design` — not on content approval in the resume handler.

`design_applied=true` and live preview artifacts must exist **before** `phase_status: awaiting_human`.

## Theme resolution

1. Brand detection (Anthropic, Google, OpenAI, Meta, Microsoft palettes)
2. Category keyword detection (cybersecurity, ai_competition, developer_skills, source_code, social_engineering)
3. Fallback: `ai_competition`

Full palette table and token JSON schema: [`design-system.md`](../_shared/design-system.md).

## HTML build requirements

- Inline CSS with design tokens as CSS custom properties
- Fixed 1080×1350 slide dimensions for all six slides
- Progress bars on content slides; badge on intro
- `.feature-grid` for closing/content structured extras
- Intro footer pinned via `.s1-content` + `.s1-main { flex: 1 }`
- Heading accent highlights (1-2 words) per [`text-formatting.md`](../_shared/text-formatting.md)

Do NOT downsize typography to fit cramped prose — restructure content instead.

## Editorial HITL gate

**Artifacts shown at review:**

- Live carousel preview (template tokens, typography, colors)
- Before/after token diff
- Slide layout thumbnails

**Human actions via `POST /workflow/resume`:**

- **Approve** — advance to images; image generation starts on images phase enter
- **Revise** — natural language feedback ("warmer palette", "larger headline") mapped to template parameter adjustments; re-runs `apply_design` deterministically

**Phase lifecycle:** `in_progress` → generate → `awaiting_human` → approve or revise (loop, max 5 revisions) → next phase.

## Python execution

Deterministic nodes: `apply_design` → `editorial_visual_pipeline.apply_design_tokens`, `run_design`

Langfuse metadata: `project_id`, `phase=design`, `agent_name=apply_design`, `content_type=carousel`
