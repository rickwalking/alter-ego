# AE-0524 — P3 — daily recovery scan and summary

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

A once-a-day scan at 04:00 BRT (PgQueuer schedule) that re-queues stuck or idle work and sends Pedro one summary, per the AE-0517 plan §4.6.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → AE-0522 (flag off) → validation → flag on →
AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- Re-enqueue approved runs with no active job; re-enqueue in-progress projects with no live lease (autopilot) and list interactive ones; one retry for recent transient-class dead letters; purge old succeeded rows and PgQueuer logs; Telegram summary; `/health` worker_last_seen + alert.

## Non-Goals

- Checkpoint pruning (AE-0525).

## Acceptance Criteria

- [ ] AC1 Given the scan runs twice on the same day (two workers or a restart), Then it acts once (schedule dedupe test).
- [ ] AC2 Given a stuck autopilot project with no live lease, When the scan runs, Then it is re-queued and resumes from its checkpoint.
- [ ] AC3 Then Pedro receives one summary message with recovered, still-dead and queue counts.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
