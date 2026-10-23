# AE-0526 — P4 — dashboard queue panel and generation-runs API

Status: Ready
Tier: T2
Priority: Medium
Type: Feature
Area: Frontend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Show the queue in /dashboard/workflow and let Pedro retry, cancel and trigger backlog themes, per the AE-0517 plan §4.7.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → validation on the
disposable droplet → AE-0522 (live on merge) → AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- "Fila" panel: queued (position, ETA, strict FIFO), backlog with "Gerar agora", running (phase, started, heartbeat), retry_wait (next attempt), dead_letter (reason, Retry/Discard), plus queue metrics.
- API `GET /api/generation-runs`, `POST …/{id}/retry`, `POST …/{id}/cancel` (owner/admin, CAS), auth tests incl. the cap bypass.

## Non-Goals

- Changing queue semantics; priorities (Pedro: strict FIFO).

## Acceptance Criteria

- [ ] AC1 Given queued, running and dead-letter runs, Then the panel shows each with the right actions and live updates.
- [ ] AC2 Given a non-owner, Then every generation-runs endpoint answers 404/403 as per the ownership rules.
- [ ] AC3 Given Pedro clicks "Gerar agora" on a backlog theme, Then it is queued outside the daily cap.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
