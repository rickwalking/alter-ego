# AE-0523 — P2 — Telegram queue position, Aprovar todas, dead-letter Retry/Discard, over-cap backlog

Status: Ready
Tier: T2
Priority: Medium
Type: Feature
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Make the queue visible and controllable from Telegram, per the AE-0517 plan §4.5 and Pedro's decisions (concurrency 1, strict FIFO, over-cap themes roll to the next day and can be triggered manually).

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → AE-0522 (flag off) → validation → flag on →
AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- Confirmar shows "Na fila: posição N de M — início estimado HH:MM"; "Aprovar todas" on the morning batch; dead-letter message with "Tentar de novo" / "Descartar" (CAS); OOM dead letters explain the render constraint.
- Over-cap themes become a backlog with `not_before` = next day's slot, max 10, 7-day expiry with one note.

## Non-Goals

- Changing the daily cap's meaning or the concurrency (Pedro: 1).

## Acceptance Criteria

- [ ] AC1 Given three theses arrive, When Pedro taps "Aprovar todas", Then three runs are queued in FIFO order and each message shows its position.
- [ ] AC2 Given a run is dead-lettered, Then Pedro receives one message with the reason and Retry/Discard, and Retry re-queues it once.
- [ ] AC3 Given more themes than the daily cap, Then the extra themes appear the next morning (and expire after 7 days).

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
