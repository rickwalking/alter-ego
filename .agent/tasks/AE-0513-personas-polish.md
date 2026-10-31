# AE-0513 — Personas polish

Status: Dev Complete
Tier: T1
Priority: Low
Type: Feature
Area: Frontend
Owner: Pedro
Agent Lane: developer → qa
Branch: feat/ae-0513-personas-polish
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

## Goal

`/dashboard/personas` reads cleanly in Portuguese and English, on desktop and on a 390 px phone: a sensible avatar
initial, translated fallbacks, tone sliders that show their value and work from the keyboard, a clear empty state and
touch-sized controls.

## Problem

Listed by Pedro as a dashboard polish item (2026-10-22 triage). Findings:

- DQ-A-11: the avatar initial is "[" for a name starting with a bracket (`neon-persona-card.tsx` used
  `name.charAt(0)`).
- DQ-A-12: "No description provided." is hard-coded English in the Portuguese list (`persona-adapter.ts`).
- Polish pass: card hierarchy (Edit/Delete floated outside the card, 10 px chips, pointer cursor on a card that is not
  clickable), slider affordance, an empty state whose title read "No personas found" with no personas at all, and
  controls under 44 px on a phone.

## Scope

- First Unicode letter of the name as the avatar initial, uppercased; a labelled person icon when there is no letter.
- Translated "Sem descrição" / "No description" and default role.
- Card: actions in the card footer (44 px), equal-height cards, 12 px chips, a "+N" chip for hidden expertise areas.
- Tone sliders: 44 px tall, visible focus ring, visible value, stacked under the label on a phone.
- Empty state: "Nenhuma persona ainda" / "No personas yet" with the primary action; the search no-match keeps its own
  title and has no action.
- 390 px: search box, form text boxes and form buttons at least 44 px tall; no horizontal scroll.

## Non-Goals

- No backend change; no persona data model change.
- No change to shared design-system atoms (NeonInput, NeonButton sizes stay as they are elsewhere).

## Acceptance Criteria

- [x] AC1 the avatar initial skips non-letters with an icon fallback.
- [x] AC2 "Sem descrição"/"No description" translated.
- [x] AC3 sliders show values, are keyboard operable and focus-visible.
- [x] AC4 empty state with the primary action, pt/en.
- [x] AC5 at 390 px no clipping, touch targets >= 44 px.
- [x] AC6 no regression of the existing persona tests (#203 form tests).

## Gherkin Scenarios

See `frontend/tests/features/personas-polish-ae0513.feature` (11 scenarios).

## Delta

### ADDED

- `frontend/src/modules/persona/components/persona-initial.ts` (+ test).
- Tests: `persona-tile.test.tsx`, `persona-tone-field.test.tsx`, `personas-empty-state.test.tsx`,
  `personas-pt-locale.test.tsx`.
- i18n keys `personas.card.{noDescription,defaultRole,avatarLabel,skillsLabel,moreSkills}`,
  `personas.empty.firstTitle` (pt, en).

### MODIFIED

- `NeonPersonaCard` (avatar, footer slot, hidden-skill chip), `mapPersonaProfileToCardProps` (translated fallbacks
  passed in), `PersonaTile`, `PersonaToneField`, `PersonasEmptyState`, personas `page.tsx`.

### REMOVED

- Hard-coded "No description provided." and "Persona" fallbacks.

## Affected Areas

- Backend: none
- Frontend: personas page and persona card
- Database: none
- API: none
- Tests: Vitest + Gherkin
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0455 (persona form, PR #203), AE-0512 (rubrics polish)

## Implementation Plan

1. Gherkin scenarios.
2. Avatar initial helper and card changes.
3. Translated fallbacks in the adapter and tile.
4. Slider, empty state and phone touch targets.
5. Screenshots before/after at 1440 and 390 px.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-31

Ticket created and implemented; see `.agent/reports/AE-0513.dev-summary.md`.

## Files Touched

See the dev summary.

## Test Evidence

See the dev summary.

## QA Report

Pending.

## Decision Log

- Phone touch targets for the shared form controls are applied from the personas page (`max-sm:` descendant
  classes) instead of changing the shared atoms, to keep the change to this page.
- The card is no longer a hover card: it is not clickable, so the pointer cursor and lift were misleading.

## Blockers

None.

## Final Summary

Pending.
