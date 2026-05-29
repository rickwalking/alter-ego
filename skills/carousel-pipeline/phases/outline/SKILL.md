---
name: carousel-pipeline-outline
description: Outline and title optimization phase of the editorial carousel workflow. Produce scroll-stopping titles and ordered slide narrative before human review.
version: 2.0.0
---

# Outline Phase

## Shared standards (read first)

- [`../_shared/critical-rules.md`](../_shared/critical-rules.md) — title criteria, fact-checking context
- [`../_shared/text-formatting.md`](../_shared/text-formatting.md) — heading accent rules, em-dash ban, paragraph length

## Purpose

Transform research findings into an ordered slide narrative with an optimized title/subtitle pair. Runs at **phase enter** via `OutlineAgent` — not on research approval in the resume handler.

## Title optimization criteria

- Scroll-stop power: does it make someone stop scrolling?
- Emotional pull: curiosity, urgency, or surprise
- Maximum ~60 characters
- Concrete > generic: specific claims beat vague statements
- No clickbait: promise must be delivered in content
- If original title is weak, propose 3 alternatives with rationale

### Weak → strong examples

| Weak | Strong |
|------|--------|
| "AI News This Week" | "3 AI Models That Changed Everything This Week" |
| "Python Tips" | "5 Python Tricks Senior Devs Use Daily" |
| "Cybersecurity Update" | "This Zero-Day Affects 90% of Web Apps" |

## Outline output shape

Return ordered slide list with:

- Slide number, `type` (`intro`, `content`, `closing`, `cta`)
- Title / key points per slide
- Estimated narrative arc summary

Title fields: `{title, subtitle}` or `{title_pt, title_en, subtitle_pt, subtitle_en}`

Default slide configuration: 1 intro, 3 content, 1 closing, 1 CTA (6 slides total).

## Editorial HITL gate

**Artifacts shown at review:** Ordered slide list with title, key points, slide type, narrative arc summary.

**Human actions via `POST /workflow/resume`:**

- **Approve** — advance to content; drafting starts on content phase enter
- **Revise** — feedback injected into `outline_planner`; supports "merge slides 3–4", "change angle", reorder slides, etc.

**Phase lifecycle:** `in_progress` → generate → `awaiting_human` → approve or revise (loop, max 5 revisions) → next phase.

## Python execution

Subagent: `outline_planner` → `OutlineAgent`

Deterministic node: `sync_slides` persists outline → DB slides via `ensure_slides_from_outline`

Langfuse metadata: `project_id`, `phase=outline`, `agent_name=outline_planner`, `content_type=carousel`
