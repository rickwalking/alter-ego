# AE-0519 — Palette archive confirm reads on one or two lines

Status: In Progress
Tier: T1
Priority: Low
Type: Bug
Area: Frontend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0519-palette-archive-confirm
Created: 2026-10-22
Updated: 2026-10-22

## Goal

The inline "Arquivar esta paleta?" confirmation on a palette card is readable at desktop and phone widths.

## Problem

Dashboard QA (DQ-C-04): after pressing "Arquivar" on a custom palette card the question wraps one word per
line. In `frontend/src/app/dashboard/palettes/palette-card.tsx` the confirm `span` (`mr-auto`) shares a
non-wrapping `justify-end` flex row with the "Cancelar" and "Arquivar" buttons, so in a narrow grid card
the buttons keep their width and squeeze the text to its longest word.

## Scope

- The confirm state renders the question on its own line above the buttons; the button row wraps when
  it has to, and the question plus both buttons form a labelled group.

## Non-Goals

- No change to the archive behaviour, the API or the copy.
- No change to the edit/archive row of the resting card.

## Acceptance Criteria

- [ ] Given Archive on a card at 1440 and 390 px, When the confirm step shows, Then "Arquivar esta paleta?"
      reads on one or two lines above the "Cancelar" / "Arquivar" buttons (its own full-width line, not a
      flex item squeezed beside them).
- [ ] Given the confirm step, Then the question and both buttons form a group named by the question, and
      Cancel returns to the resting card while Arquivar still calls the archive action once.

## Gherkin Scenarios

See `frontend/tests/features/palette-archive-confirm-ae0519.feature`.

## Affected Areas

- [x] Frontend (`palette-card.tsx`)
- [x] Tests
- Backend, API, database: no change.

## Dependencies

None.

## Progress Log

### 2026-10-22

Cause confirmed in `palette-card.tsx`; failing test first.

## Files Touched

- frontend/src/app/dashboard/palettes/palette-card.tsx
- frontend/src/app/dashboard/palettes/palette-card.test.tsx
- frontend/tests/features/palette-archive-confirm-ae0519.feature

## Test Evidence

See `.agent/reports/AE-0519.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0519.qa.md`.

## Blockers

None.
