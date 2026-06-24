# AE-0278 — (follow-up) Calendar mobile agenda view

Status: Intake
Tier: T2
Priority: Low
Type: Feature
Area: frontend
Owner: Pedro Marins
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-24
Updated: 2026-06-24
Parent: AE-0272

## Goal

Replace the `<md` horizontal-scroll month grid with a true mobile **agenda view**
(events listed chronologically by date) — the better long-term mobile pattern for a
content calendar. Filed by the GLM 5.2 review (I4) so horizontal scroll does not become
the permanent answer.

## Problem

AE-0276 ships horizontal-scroll + snap for the calendar as scoped, acknowledged debt.
A scrollable 7-col grid is still awkward on a phone; an agenda list preserves all info
and reads naturally on mobile.

## Scope (when picked up)

- `calendar/` — add an agenda renderer shown `<md`; keep the month grid `md+`.
- Reuse existing event/status meta; no backend changes.

## Acceptance Criteria (draft)

- [ ] Below `md`: events render as a dated, chronological agenda list (no horizontal scroll).
- [ ] At `md+`: the existing month grid is unchanged.
- [ ] Neon identity preserved; `.feature` scenarios; gates green.

## Notes

Not part of the AE-0272 epic delivery. Backlog until prioritized.
</content>
