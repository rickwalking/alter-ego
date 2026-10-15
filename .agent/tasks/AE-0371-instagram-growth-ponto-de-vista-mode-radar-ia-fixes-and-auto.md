# AE-0371 — Instagram growth: Ponto de Vista mode, Radar IA fixes and autopilot wiring

Status: Dev Complete
Tier: T3
Priority: High
Type: Epic
Area: Cross-cutting
Owner: Claude (autonomous worker)
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0371-growth-pov-mode
Kanban Card: TBD
Parent: none
Created: 2026-10-15
Updated: 2026-10-15

## Goal

Turn the owner's Instagram growth plan (section 16) into product: a new "Ponto de Vista" (`pov`) carousel mode next to the current "Radar IA" (`news_analysis`), the Radar IA fixes, autopilot wiring for POV and per-post Instagram insights. Plan: [docs/architecture/instagram-growth-pov-mode.md](../../docs/architecture/instagram-growth-pov-mode.md); ADR-0021.

## Problem

The account is flat (336 followers, ~0.9 shares and ~0.1 saves per carousel). AI-news recaps give nobody a reason to send, save, argue or follow. The pipeline only knows one fixed 7-slide news layout with generic AI art, a PT slide that says "Swipe", a 12-18 hashtag double-CTA caption and no place for the owner's opinion.

## Scope

- Coordinate AE-0372 (R1) → AE-0373 (R2) → AE-0374 (R3) → AE-0375 (R4) → AE-0376 (R5) → AE-0377 (R7 + R6 glue) → AE-0378 (R8), one branch (`feat/ae-0371-growth-pov-mode`), one commit series per child.
- Dev summary with per-ticket change table, gate results, migration SQL, owner actions (R0) and follow-ups.

## Non-Goals

- R0 owner actions (UI only, listed below).
- R6 scheduler: owned by AE-0370 (`fix/ae-0370-scheduled-publish`). This epic adds only the POV slot glue (AE-0377), wired into AE-0370's publish choice after merging it.
- Reels / video, paid tools, boosting.
- Inventing opinions, experiences, test results or numbers in prompts or fixtures.

## Acceptance Criteria

- [x] WHEN every child ticket is Dev Complete THE epic dev summary SHALL contain the per-ticket change table, the GATES_JSON results, the exact migration SQL, the owner actions and the follow-ups.
- [x] WHEN a carousel is created without a mode THE SYSTEM SHALL behave as Radar IA (`news_analysis`), with existing projects keeping their stamped policy and prompts.
- [x] WHEN the owner creates a POV carousel with a thesis THE SYSTEM SHALL produce an 8-10 slide first-person deck whose slide 1 is a hook over the owner's photo.
- [x] WHEN any POV prompt is rendered THE SYSTEM SHALL instruct the model never to invent opinions, experiences, test results or numbers.

## Gherkin Scenarios

```gherkin
Feature: Instagram growth modes

  Scenario: Radar IA stays the default
    Given a carousel created without a content mode
    When the workflow generates its outline
    Then it uses the Radar IA contract and prompts

  Scenario: Ponto de Vista carousel from the owner's thesis
    Given a POV carousel with a thesis and 9 slides
    When the workflow generates its outline and content
    Then the deck has 9 slides in the POV role order with the hook on slide 1

  Scenario: POV without a thesis is rejected
    Given a POV create request without a thesis
    When it is submitted
    Then the API answers 422 and nothing is created
```

## Delta

### ADDED

- Coordinate AE-0372 (R1) → AE-0373 (R2) → AE-0374 (R3) → AE-0375 (R4) → AE-0376 (R5) → AE-0377 (R7 + R6 glue) → AE-0378 (R8), one branch (`feat/ae-0371-growth-pov-mode`), one commit series per child.
- Dev summary with per-ticket change table, gate results, migration SQL, owner actions (R0) and follow-ups.

### MODIFIED

- See Scope.

### REMOVED

- None.

## Affected Areas

- Backend: carousel domain/API/services, presentation policy, prompts, layouts, creator assets, images node, autopilot intake/runner/Telegram, insights
- Frontend: create wizard, outline review, dashboard
- Database: additive columns on carousel_projects, carousel_creator_assets, topic_candidates, autopilot_runs; new instagram_post_insights
- API: carousel create/response fields, PUT hook, creator-asset list, insights
- Tests: Gherkin per child, rule-fires tests for new validator codes
- Docs: docs/architecture/instagram-growth-pov-mode.md, ADR-0021, carousel-pipeline skill docs
- Prompts/LLM: carousel_pov/v1, carousel/v7, scout v3
- Observability: Langfuse metadata `content_type` / `phase` unchanged
- Deployment: manual migration SQL before deploy; no new env var

## Dependencies

- Blocks: none
- Blocked by: AE-0370 should merge first (migration re-chain)
- Related: ADR-0021, ADR-0020, AE-0348, AE-0370

## Implementation Plan

1. Architect plan + ADR + tickets (this commit), skeptical review, fixes.
2. Implement children in roadmap order, test first, Gherkin per behaviour change.
3. READY FOR GATES rounds after R1, R3, R5 and at the end.

## Owner actions (R0, no code)

1. **Persona "Pedro":** `/dashboard/personas` → Nova persona. Voice: "direto, primeira pessoa,
   builder/arquiteto, sem hype". Signature line: "Sou arquiteto de soluções e construo apps com
   IA." Forbidden phrases: "revolucionário", "game changer", "você não vai acreditar",
   "o futuro chegou". Writing samples: paste the captions of the Sep 14 and Oct 3 posts.
   The wizard preselects the persona named "Pedro" in both modes (AE-0373).
2. **Photos:** take 10-15 photos in one session (pointing, thinking, arms crossed, at the
   laptop), cut them out on the phone ("lift subject"), export PNG/WebP ≤5 MB. Upload them in
   the wizard's "Foto do slide 1" picker with role `hook` (AE-0376); upload the round avatar
   with role `cta`.
3. **Next posts:** pick Tutorial/Comparison + Flat Editorial (now the default, AE-0372) or the
   new POV mode; keep captions to 3-5 hashtags and one CTA (caption v7 does this).
4. **Calendar:** book Tue/Thu 12:00 BRT slots. Once AE-0370 is live, set
   `AUTOPILOT_DEFAULT_PUBLISH=next_slot` if you want Approve to schedule automatically.
5. **Housekeeping:** archive the 15 rejected Brief cards; enable the editorial-analytics
   feature flag if you want the editorial card (AE-0378 explains the error otherwise).
6. **Scout v3:** point the Cursor Grok Bot routine at `ops/grokbot/grok-bot/v3/routine.md`
   (AE-0377); v2 keeps working until you switch.


## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-15 10:00

Ticket written from the architect plan (docs/architecture/instagram-growth-pov-mode.md).

### 2026-10-15 (dev)

All children (AE-0372 … AE-0378) Dev Complete on `feat/ae-0371-growth-pov-mode`, in roadmap
order R1 → R2 → R3 → R4 → R5 → R7 → R8. Relay rounds after R1 (PASS), after R3 (no result in
the 60-minute window; a regression it would have caught was found locally and fixed), after
R5 and at the end — see the dev summary.

## Files Touched

See each child ticket's Files Touched and the per-ticket table in
`.agent/reports/AE-0371.dev-summary.md`; plan `docs/architecture/instagram-growth-pov-mode.md`
(§10 as built), ADR-0021, `docs/architecture/grokbot-autopilot.md` (§4, §5.5).

## Test Evidence

Static backend gates 16/16 PASS on each roadmap head (R1, `33a0884`, `59f87e4`, `b74de79`,
`2acb7fe`); targeted backend unit/integration suites and frontend typecheck/lint/vitest
listed per ticket; relayed DB gates in `.agent/reports/AE-0371.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- 2026-10-15 — **Roles, not new slide types** (ADR-0021): POV roles map onto intro/content/summary/cta
  so validators, translation and autopilot gates keep working.
- 2026-10-15 — **Radar IA caption goes in `carousel/v7/`**, not `carousel/v3/` as the plan says:
  `v3/` already exists (outline/content) and existing prompt versions are never edited.
- 2026-10-15 — **No prompt registry change:** the registry discovers families by directory; the
  plan's "register in registry.py" is stale.
- 2026-10-15 — **Image default = `flat_editorial`** everywhere (16.4 #7: "prefer flat_editorial";
  R0 also picks Flat Editorial). Scout-chosen styles still win.
- 2026-10-15 — **New Radar IA projects are stamped `hero_lower_third_v4`**; v1–v3 projects keep
  their frozen policy and prompts (owner: "v2 stays v2").
- 2026-10-15 — **Mode read from the project row** at generation time (no new LangGraph state).
- 2026-10-15 — **POV rubric heuristics are warnings** (`first_person_missing`, `thesis_not_early`);
  only objective ones block (`hook_word_limit`, `slide_count_invalid`). "At most one news
  slide" is structural (one `news` role slot), so it has no validator (AE-0374).
- 2026-10-15 — **R6 glue unwired:** AE-0370 is not on `main`; `PublishSlotPolicy` +
  `PovPublishSlots` ship isolated, wiring is a follow-up after AE-0370 merges.
- 2026-10-15 — **Migrations chain from `f8a9b0c1d2e3`**; re-point onto AE-0370's head when
  merging `main` after AE-0370 lands. Prod SQL is idempotent (`IF NOT EXISTS`).
- 2026-10-15 — **AE-0370 merged into this branch** (orchestrator, before PR 105 lands):
  `b0c1d2e3f4a5` now revises `a9b0c1d2e3f4`, one head `c2d3e4f5a6b7`. The R6 glue is wired:
  `publish_choice` asks `publish_slots_for(run, now)`; the `PublishSlotPolicy` Protocol stub
  was removed. A run is POV when it has a confirmed `pov_thesis` (the only POV marker on the
  run; POV runs cannot reach review without one). In `next_slot` mode a POV run is scheduled
  for the next Tue/Thu 12:00; the Agendar menu shows that slot first, then AE-0370's next two.
- 2026-10-15 — **Skeptical review** (gemini-2.5-pro, blind): BLOCK → resolved; see
  `.agent/reports/AE-0371.skeptical-review.md` (roles stamped by position, rollback documented,
  merge order fixed, POV inputs create-only).

## Blockers

None.

## Final Summary

Pending.
