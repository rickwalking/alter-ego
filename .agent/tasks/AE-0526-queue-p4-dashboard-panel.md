# AE-0526 — P4 — dashboard queue panel and generation-runs API

Status: Done
Tier: T2
Priority: Medium
Type: Feature
Area: Frontend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: feat/ae-0526-queue-panel
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-24

## Goal

Show the queue in /dashboard/workflow and let Pedro retry, cancel and trigger backlog themes, per the AE-0517 plan §4.7.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → validation on the
disposable droplet → AE-0522 (live on merge) → AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- "Fila de geração" panel above the active workflow board (admin only; hidden for editors): active runs in FIFO order
  (running first, then queued with a start estimate, retry-waiting with the next attempt), the runs the queue parked
  with "Tentar de novo" / "Descartar" (autopilot) or a link to the editor (dashboard resumes), the backlog with its
  expiry and "Gerar agora", and the average drive time. Polls like the board and on focus; a button reloads it.
- API (admin only): `GET /api/generation-runs`, `POST /api/generation-runs/{id}/retry|discard|cancel`,
  `POST /api/generation-runs/backlog/{candidate_id}/generate`. Every action is a compare-and-set: done → 200, already
  resolved / not allowed → 409, unknown → 404. Retry and discard reuse the Telegram buttons' revive/discard. Cancel
  only takes an autopilot run that has not started out of the queue (its run ends `failed`, owner's reason); a running
  drive or a dashboard resume is never cancelled here.

## Non-Goals

- Changing queue semantics; priorities (Pedro: strict FIFO). Server-sent updates for the panel (it polls).

## Acceptance Criteria

- [ ] AC1 Given queued, running and dead-letter runs, Then the panel shows each with the right actions and refreshes
  on the board's poll, on focus and after every button.
- [ ] AC2 Given a non-admin, Then every generation-runs endpoint answers 403 and the panel is hidden.
- [ ] AC3 Given Pedro clicks "Gerar agora" on a backlog theme, Then it is queued outside the daily cap, once.
- [ ] AC4 Given a parked autopilot run, Then retry puts it back in the queue once and discard closes it; given a queued
  autopilot run that has not started, Then cancel takes it out.

## Gherkin

`backend/tests/features/queue_board_api_ae0526.feature`, `frontend/tests/features/workflow-queue-panel.feature`.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
- 2026-10-24 (Pedro: no feature flags, strict FIFO, concurrency 1): the panel is admin only (the owner); the
  backlog endpoint lives under `/api/generation-runs` because `/api/autopilot/*` is reserved for the GrokBot API-key
  routes; cancel is limited to autopilot runs that have not started (cancelling a dashboard resume or a drive between
  gates would leave the project half-driven).

## Final Summary

Merged to `main` in PR #288 (b30b4758, 2026-10-25). The status was left open after the merge; closed on 2026-10-30 (ticket housekeeping, no code change).
