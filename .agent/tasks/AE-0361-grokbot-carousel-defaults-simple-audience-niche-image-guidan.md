# AE-0361 — GrokBot carousel defaults: simple audience/niche, image guidance and preset

Status: Dev Complete
Tier: T2
Priority: High
Type: Feature
Area: backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: rickwalking/ae-0361-grokbot-carousel-defaults
Kanban Card: TBD
Created: 2026-10-14
Updated: 2026-10-14
Parent: AE-0348

## Goal

Every carousel GrokBot creates carries:

1. A **target audience** in simple words.
2. A **niche and brief** in simple words that keep the carousel on the selected theme.
3. **Image guidance**: futuristic anime in the style of Akira, Ghost in the Shell and Evangelion by default, with a theme-specific background. The palette theme is always `auto` and the image preset is OpenAI Neo-Anime by default. Other presets are used for more specific themes.

## Problem

The scout's `audience`, `niche` and `brief` are free text up to 120/80/800 characters. Nothing checks that they are short or that the brief covers the topic. The autopilot creates carousels with the global image defaults and no visual direction, so the owner's usual anime style and theme-specific backgrounds are never requested.

## Scope

- `TopicProposal` gains `image_style` (enum, default `neo_anime`) and `image_guidance` (optional, ≤400 chars, plain text, no URLs).
- Simple-words rules, each a per-proposal rejection (the rest of the batch still passes):
  - `audience` 1–3 words → `audience_not_simple`
  - `niche` 1–3 words → `niche_not_simple`
  - `brief` ≤600 chars → `brief_not_simple`
  - `brief` mentions at least one significant title keyword (casefolded, stop words ignored) → `brief_off_theme`
- `topic_candidates` persists `image_style` and `image_guidance` (additive Alembic revision, single head).
- The runner's `ProjectSpec` carries the style and the resolved guidance. The editorial driver creates the carousel with `image_model=openai`, `theme=auto`, `image_style` and `custom_visual_details`.
- When the bot omits guidance, the backend builds it from a constant template (anime references for `neo_anime`, style-neutral wording otherwise, plus `Background: <niche>-themed setting.`).
- The Telegram review message gains one line: `Audience · Niche · Style`.
- Routine pack `ops/grokbot/grok-bot/v2/` with the rules and the image-style decision table. README points to v2. v1 is untouched.
- Docs: `docs/architecture/grokbot-autopilot.md` §5.3 "Carousel defaults".

### Image-style decision table

| Theme of the topic | image_style |
|---|---|
| Default: AI agents, models, AGI, LLM launches, robotics/automation, cybersecurity, future of work, most AI themes | `neo_anime` |
| Data, benchmarks, how-to/tutorials, business strategy or ROI explainers | `flat_editorial` |
| Physical hardware launches: chips, GPUs, devices, consumer gadgets | `hyperreal` |
| Regulation, policy, ethics, society or real-world events involving people | `cinematic` |
| Humor, memes, hype or internet culture | `comic_neon` |

## Non-Goals

- Bot-selected image model or palette theme (the backend always sets `openai` / `auto`).
- Changing the web carousel-creation UI or the editorial workflow.
- Editing `ops/grokbot/grok-bot/v1/`.

## Acceptance Criteria

- [x] AC1 — WHEN a proposal omits `image_style`, THE intake SHALL store `neo_anime`.
- [x] AC2 — WHEN a proposal sets `image_style` to a preset outside the openai-supported set, THE API SHALL return 422 and store nothing.
- [x] AC3 — WHEN `audience` or `niche` has zero or more than 3 words, THE intake SHALL reject that proposal with `audience_not_simple` / `niche_not_simple` and still accept the others.
- [x] AC4 — WHEN `brief` shares no significant keyword with `title` (stop words ignored), THE intake SHALL reject it with `brief_off_theme`. WHEN it is longer than 600 chars, THE intake SHALL reject it with `brief_not_simple`.
- [x] AC5 — WHEN `image_guidance` contains a URL, THE intake SHALL reject the proposal with `url_in_text`.
- [x] AC6 — WHEN the runner creates the carousel, THE editorial driver SHALL pass `image_model=openai`, `theme=auto`, the stored `image_style`, and `custom_visual_details` = the stored guidance, or the template when none was sent.
- [x] AC7 — WHEN the owner review message is sent, THE keyboard message SHALL start with `Audience: … · Niche: … · Style: …`.
- [x] AC8 — THE topic-candidate columns SHALL be added by an additive revision that is the single Alembic head and downgrades cleanly.
- [x] AC9 — THE v2 routine SHALL state the simple-words rules, the decision table, and the `image_guidance` background rule. The v2 examples SHALL validate against the API schemas and the v2 example SHALL pass the intake rules.

## Gherkin Scenarios

See `backend/tests/features/autopilot_carousel_defaults.feature`.

```gherkin
Feature: GrokBot carousel defaults

  Scenario: Default neo_anime style and template guidance
    Given a proposal with no image_style and no image_guidance
    When the scout posts the batch
    Then the candidate is stored with image_style "neo_anime"
    And the carousel is created with the anime template guidance and a niche background

  Scenario: Invalid image style is rejected
    Given a proposal with image_style "watercolor"
    When the scout posts the batch
    Then the response is 422 and nothing is stored
```

## Delta

### ADDED

- `modules/autopilot/domain/carousel_defaults.py`, `carousel_constants.py`
- Alembic revision `e7f8a9b0c1d2` (topic_candidates.image_style, image_guidance)
- `ops/grokbot/grok-bot/v2/`

### MODIFIED

- Topic intake schema, domain plan, stores, runner spec, editorial driver, review notice.
- `CarouselReviewRow` (editorial facade) gains audience, niche, image_style.

### REMOVED

- None.

## Affected Areas

- Backend: `modules/autopilot`, `modules/editorial/infrastructure/carousel_automation.py`
- Frontend: none
- Database: `topic_candidates` +2 columns
- API: `POST /api/autopilot/topics` (two optional fields, four new rejection reasons)
- Tests: unit + integration + migration
- Docs: `docs/architecture/grokbot-autopilot.md` §5.3
- Prompts/LLM: routine pack v2 (file)
- Observability: none
- Deployment: one additive migration

## Dependencies

- Blocks: none
- Blocked by: AE-0348 (PR #92 base)
- Related: AE-0360

## Implementation Plan

1. Gherkin feature.
2. Domain rules + constants, schema, mapping.
3. Persistence + migration.
4. Runner spec + editorial driver.
5. Review line.
6. Routine pack v2, README, drift test, docs.

## QA Checklist

- [x] Security reviewed (no URLs in guidance, enum-only style, no new secrets)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-14 12:00

Ticket created from the owner brief. Implementation started.

### 2026-10-14 15:00

Implementation complete. Full `gate-capture.sh backend` run: 21 PASS / 0 FAIL / 0 SKIP (pytest 3576 passed, diff coverage 96%, mutation 78.56%). Moved to Dev Complete. See `.agent/reports/AE-0361.dev-summary.md`.

## Files Touched

See `.agent/reports/AE-0361.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0361.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- `image_style` is a schema enum, so an unknown preset is a 422 for the batch (like unknown keys). The domain also re-checks the `(openai, style)` combo against `SUPPORTED_IMAGE_COMBOS` as a drift guard.
- The simple-words rules are per-proposal rejections so one weak proposal does not drop the batch.
- `brief` >600 chars uses its own reason `brief_not_simple`. The schema limit stays at 800 so the batch is not 422'd.
- Guidance is stored as sent (nullable). The runner resolves the template, so rows created before this change also get guidance.

## Blockers

None.

## Final Summary

Pending.
