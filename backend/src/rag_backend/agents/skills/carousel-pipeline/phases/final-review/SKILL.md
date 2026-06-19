---
name: carousel-pipeline-final-review
description: Final review phase of the editorial carousel workflow. Bundle carousel preview, bilingual blog, quality scores, and caption before publish approval.
version: 2.0.0
---

# Final Review Phase

## Shared standards (read first)

- [`../_shared/export-and-caption.md`](../_shared/export-and-caption.md) — Playwright export, caption structure, blog rules, publish vs approve
- [`../_shared/content-contracts.md`](../_shared/content-contracts.md) — bilingual JSON/blog shape, slide contracts
- [`../_shared/critical-rules.md`](../_shared/critical-rules.md) — fail-loudly, bilingual storage

## Purpose

Compose final blog bundle, run quality scoring, generate Instagram caption, and export slide JPGs. Human reviews the complete artifact set before `approved_for_publish`.

Nodes: `compose_blog`, `score_quality` (`QualityAgent`), `caption_writer` / `run_caption`, Playwright export via `CarouselExportTool`.

## Export checklist

Before marking review-ready:

- All six slides exported at **1080×1350**, quality 95 JPEG
- Self-contained HTML with base64 data URIs
- Bilingual blog markdown in `blog_translations`
- Instagram caption with hook, value promise, comment question, double CTA, 12-18 hashtags

Full export process and caption example: [`export-and-caption.md`](../_shared/export-and-caption.md).

## Quality rubric (review payload)

Include from `QualityAgent`:

- Persona voice score
- Forbidden phrase check
- Materials attribution check
- Rubric scores

## Editorial HITL gate

**Artifacts shown at review:**

- Full carousel preview (slides + design)
- Blog markdown preview (both locales if available)
- Rubric scores from `QualityAgent`
- Instagram caption draft and LinkedIn post snippets
- Checklist: persona score, forbidden phrases, materials attribution

**Human actions via `POST /workflow/resume`:**

- **Approve** — sets `approved_for_publish`, `quality_passed: true`, `current_phase: final_review`. Does **not** set `is_public`. Publish is a separate explicit action.
- **Revise** — routes to earlier phase (research, outline, content, design, images) based on feedback classification or explicit user selection ("send back to content")

**Phase lifecycle:** `in_progress` → compose + score + export → `awaiting_human` → approve or revise (loop, max 5 revisions) → `approved_for_publish`.

## Publish (separate from approve)

After final approval, publish via `POST /publish` or publish panel. Workspace preview uses authenticated `/preview/*` routes — never public-cacheable until published.

## Python execution

- `compose_blog` — blog node
- `score_quality` — `QualityAgent`
- `caption_writer` — caption prompt / `run_caption`
- `CarouselExportTool` — Playwright screenshots

Langfuse metadata: `project_id`, `phase=final_review`, `agent_name` per node, `content_type=carousel`. Human review events link to active trace.
