---
name: carousel-pipeline-content
description: Content drafting phase of the editorial carousel workflow. Generate bilingual slide copy and blog markdown matching slide-type contracts before human review.
version: 2.0.0
---

# Content Phase

## Shared standards (read first)

- [`../_shared/content-contracts.md`](../_shared/content-contracts.md) — JSON shape, slide types, structured extras, image_prompt contract
- [`../_shared/text-formatting.md`](../_shared/text-formatting.md) — bold vs code, heading highlights, em-dash ban
- [`../_shared/anti-patterns.md`](../_shared/anti-patterns.md) — stub slides, closing prose wall, JSON parse failures

## Purpose

Generate 6-slide carousel copy plus bilingual blog post (`blog_pt`, `blog_en`). Runs at **phase enter** via `ContentDraftAgent` + `PersonaAgent.enforce()` — not on outline approval in the resume handler.

All slide drafts must exist **before** `phase_status: awaiting_human`.

## Slide structure

| # | Type | Content |
|---|------|---------|
| 1 | `intro` | Hook + hero image prompt |
| 2-4 | `content` | Deep information with stats/quotes/structured extras |
| 5 | `closing` | Actionable takeaways as checklist (`features` array) |
| 6 | `cta` | Save + share prompt |

Full JSON return shape and per-type body contracts: [`content-contracts.md`](../_shared/content-contracts.md).

## Writing rules

- pt-BR: informal Brazilian Portuguese, engaging
- EN: professional, direct, same depth and structure
- NEVER use em dashes in either language
- Short paragraphs (2-4 sentences max)
- Cross-slide distinctness (AE-0291): each slide MUST cover a distinct angle. Do
  not repeat another slide's framing, examples, statistics, or sentences. The
  other slides' headings and key points are supplied under "Other slides in this
  carousel" — differentiate wording and concrete detail against them.
- One structured extra per content slide (`stats`, `features`, or `insight`)
- Tool vocabulary: Claude Code, OpenCode, BMAD, Superpowers, Cursor (Copilot valid but dated alone)

## Persona gate (before review interrupt)

`PersonaAgent.enforce()` runs after drafting, before the content review interrupt:

- Voice match score must be >= 70 before human approval in UI
- Forbidden phrases are blockers, not suggestions
- Include persona score and forbidden phrase warnings in review payload

## Editorial HITL gate

**Artifacts shown at review:**

- Per-slide `draft_text`
- Persona voice score and forbidden phrase warnings
- Side-by-side outline reference

**Human actions via `POST /workflow/resume`:**

- **Approve** — advance to design; token application starts on design phase enter
- **Revise** — per-slide or global feedback; parallel subagent respawn for flagged slides only

**Phase lifecycle:** `in_progress` → generate → persona enforce → `awaiting_human` → approve or revise (loop, max 5 revisions) → next phase.

## Python execution

Subagent: `content_drafter` → `ContentDraftAgent`, `PersonaAgent.enforce`

Langfuse metadata: `project_id`, `phase=content`, `agent_name=content_drafter`, `content_type=carousel`
