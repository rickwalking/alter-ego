---
status: proposed
date: 2026-10-15
decision-makers: Pedro Marins
consulted: Claude (architecture plan, AE-0371)
informed: delivery team
---

# ADR-0021: Content mode "Ponto de Vista" as roles on top of the existing carousel pipeline

## Context and Problem Statement

The owner's Instagram growth plan (2026-10-14 audit) found that AI-news recaps do not grow
the account: they give nobody a reason to send, save, argue or follow. The plan asks for a
second carousel mode, **Ponto de Vista** (`pov`): first-person, opinionated, hook-first, the
owner's face on slide 1, 8–10 slides. The existing approach becomes **Radar IA**
(`news_analysis`) and stays the default.

The carousel pipeline is built around one fixed 7-slide sequence. Five slide types (`intro`,
`summary`, `content`, `closing`, `cta`) key every validator, copy budget, casing rule,
translator, artifact-health check and layout lookup. The outline normalizer forces that
sequence by position. Presentation contracts are immutable, versioned YAML files, and prompts
are immutable, versioned folders.

How do we add a mode with a different narrative, a variable slide count and different visuals
without destabilising the live Radar IA pipeline and the autopilot built on it?

## Decision Drivers

- Existing and in-flight carousels must keep their frozen semantics (contracts and prompts are
  immutable; "v2 stays v2").
- The autopilot gates (outline count, hero images, persona ≥70, presentation blockers) must
  keep working unchanged for both modes.
- The model may sharpen the owner's thesis but must never invent it, nor experiences or
  numbers.
- Prod runs Python 3.11; migrations are additive and applied by hand.

## Considered Options

1. **New slide types** (`hook`, `rehook`, `pov`, `point`, `twist`, `save`) everywhere.
2. **A separate POV pipeline** (own workflow graph, own renderer).
3. **Roles on top of the existing slide types:** a new contract declares a `role` per slide
   that maps to an existing slide type; the mode picks the contract, the prompt family and
   the layout strategy per role.

## Decision Outcome

Chosen: **Option 3**.

- The project gains `content_mode` (`NULL` = `news_analysis`) and the POV inputs (thesis,
  personal proof, format, slide count, CTA goal, slide-1 photo); `persona_id` is now written
  at creation.
- New contract `pov_hook_v1.yaml` (8–10 slides via `slide_count_min/max` and optional `point`
  slides) and `hero_lower_third_v4.yaml` for new Radar IA projects (optional 8th twist slide,
  no artwork on summary/closing). v1–v3 stay as they are.
- New prompt families `carousel_pov/v1` and `carousel/v7`; earlier versions stay frozen.
- Generators read the mode from the project row at generation time (no new LangGraph state).
- New layout strategies are selected by role; slides without a role use today's lookup.
- New POV rubric items are deterministic validators; heuristic ones are warnings so they can
  never block the autopilot.

### Consequences

- Good, because validators, casing repair, translation, artifact build and autopilot gates
  work on POV decks without per-type changes.
- Good, because legacy outlines take the unchanged positional path (role path only when every
  slide carries a known role).
- Good, because POV images are mostly the uploaded photo and solid slides, which cuts image
  spend per carousel.
- Bad, because a role is a second axis next to slide type: two contracts (`v4`, `pov_hook_v1`)
  and the role→strategy map must stay consistent (covered by loader validation and tests).
- Bad, because copy budgets stay keyed by slide type, so role-specific limits tighter than the
  type budget (e.g. rehook ≤90) are prompt guidance, not validator blockers; only
  `hook_word_limit` is enforced per role.
- Neutral, because the autopilot needs a thesis-confirmation step before POV generation (new
  run state), which adds one Telegram interaction per POV run.

## More Information

- Plan: [instagram-growth-pov-mode.md](../architecture/instagram-growth-pov-mode.md)
- Epic: AE-0371 (children AE-0372 to AE-0378). Scheduling (roadmap R6) is AE-0370.
- Related: ADR-0003 (persona-driven content), ADR-0007 (carousel pipelines), ADR-0020
  (GrokBot autopilot).
- Extended by [ADR-0023](0023-content-mode-pov-news.md): `pov_news`, a POV-family mode with a
  news-analysis voice and scout-verified quotes (AE-0406).
