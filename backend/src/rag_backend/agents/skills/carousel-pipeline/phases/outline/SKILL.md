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

### Weak → strong examples (AE-0372: hooks with a point of view, not headlines)

Slide 1 is a hook, not a news headline: up to 10 words, it must make sense to a
stranger with no context, and the carousel must pay it off. Never put a number,
test or result in a hook that the sources (or the owner's own proof) do not back.

| Weak (recap headline) | Strong (hook formula) |
|------|--------|
| "Novidades de IA da semana" | "Todo mundo falou do [lançamento]. Ninguém falou do que importa." (lacuna de curiosidade) |
| "Novo modelo lançado" | "O que o [modelo] muda pra quem programa" (impacto para você) |
| "Dicas de prompt" | "Pare de pedir código pra IA. Peça isso no lugar." ("Pare de…") |
| "IA no trabalho" | "Como eu uso IA para revisar uma arquitetura" (primeira pessoa + resultado) |
| "IA e empregos" | "A IA não vai roubar seu emprego. Sua falta de critério vai." (opinião contrária) |

Radar IA angle (growth plan 16.4 #1): at most one slide on what happened, at least
three on what it changes for the reader, and the closing slide is the owner's verdict.

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
