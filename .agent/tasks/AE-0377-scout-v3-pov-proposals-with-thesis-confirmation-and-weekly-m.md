# AE-0377 — Scout v3: pov proposals with thesis confirmation and weekly mix

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Feature
Area: backend
Owner: Claude (autonomous worker)
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0371-growth-pov-mode
Kanban Card: TBD
Parent: AE-0371
Created: 2026-10-15
Updated: 2026-10-15

## Goal

Let the autopilot propose POV topics whose thesis the owner confirms on Telegram before generation, keep the weekly mix, and add the POV slot glue for AE-0370 (roadmap R7 + R6 glue).

## Problem

The scout only ranks "highest viral potential" news; the autopilot can only make Radar IA recaps and has no way to take the owner's thesis.

## Scope

- `ops/grokbot/grok-bot/v3/{routine.md,topics.example.json}` with `mode`, `thesis_draft`, debate angle (v2 kept).
- Intake accepts `mode`/`thesis_draft`; migration on `topic_candidates` and `autopilot_runs`.
- Run state `awaiting_thesis` + Telegram confirm/edit/discard; confirmed thesis copied to the project; expiry after 72 h.
- Weekly cap: ≤1 Radar IA run per São Paulo ISO week.
- `PovPublishSlots` (Tue/Thu 12:00 BRT) + `publish_slots_for`, wired into AE-0370's publish choice (next_slot mode and the Agendar menu).

## Non-Goals

- Building a scheduler or wiring `next_slot` (AE-0370 + follow-up).
- Letting the LLM decide the owner's opinion.

## Acceptance Criteria

- [x] WHEN a scout v2 proposal (no mode) arrives THE SYSTEM SHALL treat it as `news_analysis` exactly as today.
- [x] WHEN a POV proposal without `thesis_draft` arrives THE SYSTEM SHALL reject it (`thesis_missing`).
- [x] WHEN a POV run is queued THE SYSTEM SHALL ask the owner on Telegram to confirm, edit or discard the draft thesis before creating the carousel.
- [x] WHEN the owner confirms or replies with an edited thesis THE SYSTEM SHALL store it and start generation once; a double tap SHALL start it once.
- [x] WHEN a non-owner taps a thesis button THE SYSTEM SHALL ignore it.
- [x] WHEN a Radar IA proposal arrives in a São Paulo week that already has one THE SYSTEM SHALL reject it with `weekly_news_cap_reached`.
- [x] WHEN the POV slot policy is asked for the next slot THE SYSTEM SHALL return the next Tuesday or Thursday 12:00 America/Sao_Paulo at least 15 minutes ahead.

## Gherkin Scenarios

```gherkin
Feature: Autopilot POV thesis

  Scenario: Owner confirms the draft thesis
    Given a queued POV run with a draft thesis
    When the owner taps Confirmar
    Then the run starts generation with that thesis

  Scenario: Owner edits the thesis
    Given a POV run awaiting its thesis
    When the owner taps Editar and replies with a new thesis
    Then the run starts generation with the owner's text

  Scenario: Owner discards
    When the owner taps Descartar
    Then the run is rejected and nothing is generated

  Scenario: Second news run in the same week
    Given a news_analysis run created this São Paulo week
    When another news_analysis proposal arrives
    Then it is rejected with weekly_news_cap_reached

  Scenario: Next POV slot
    Given it is Tuesday 11:50 in São Paulo
    When the next POV slot is computed
    Then it is Thursday 12:00
```

## Delta

### ADDED

- `ops/grokbot/grok-bot/v3/{routine.md,topics.example.json}` with `mode`, `thesis_draft`, debate angle (v2 kept).
- Intake accepts `mode`/`thesis_draft`; migration on `topic_candidates` and `autopilot_runs`.
- Run state `awaiting_thesis` + Telegram confirm/edit/discard; confirmed thesis copied to the project; expiry after 72 h.
- Weekly cap: ≤1 Radar IA run per São Paulo ISO week.
- `PovPublishSlots` (Tue/Thu 12:00 BRT) + `publish_slots_for`, wired into AE-0370's publish choice (next_slot mode and the Agendar menu).

### MODIFIED

- See Scope.

### REMOVED

- None.

## Affected Areas

- Backend: modules/autopilot intake/runner/state machine/Telegram, new pov files
- Frontend: none
- Database: topic_candidates.content_mode/thesis_draft, autopilot_runs.pov_thesis
- API: x-signals/topics intake schema (`mode`, `thesis_draft`)
- Tests: unit + `autopilot_pov_thesis.feature`
- Docs: grokbot-autopilot.md, ops scout v3
- Prompts/LLM: scout routine v3
- Observability: none
- Deployment: manual SQL; switch the Grok Bot routine to v3

## Dependencies

- Blocks: none
- Blocked by: AE-0375, AE-0376
- Related: AE-0370, AE-0348

## Implementation Plan

1. Gherkin
2. scout v3
3. intake + migration
4. thesis state + Telegram
5. weekly cap
6. slot glue

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

Implemented in b74de79 on `feat/ae-0371-growth-pov-mode`. Ready for the final relay round.

## Files Touched

Scout v3 pack (`ops/grokbot/grok-bot/v3`), intake mode/thesis + weekly Radar IA cap, `awaiting_thesis` state, `thesis.py`, `thesis_prompts.py`, `thesis_actions.py`, `run_spec.py`, `pov_schedule.py`, `pov_project.py`, migration `b1c2d3e4f5a6`, docs, tests + `autopilot_pov_thesis.feature`.

## Test Evidence

Static gates 16/16 PASS on `b74de79`; autopilot unit 606 passed; autopilot integration (intake, QA r1, hero images, migrations) green after adapting the daily-cap tests to the weekly Radar IA cap.

Gate details and GATES_JSON: `.agent/reports/AE-0377.dev-summary.md` and the epic summary `.agent/reports/AE-0371.dev-summary.md`.

## QA Report

Pending.

## Decision Log

- 2026-10-15: The weekly cap behaves like the daily cap: an extra Radar IA topic is stored but not queued and is listed under `weekly_news_cap_reached`.
- 2026-10-15: design per ADR-0021 and the architect plan; see the epic AE-0371 Decision Log for cross-cutting decisions.

## Blockers

None.

## Final Summary

Pending.
