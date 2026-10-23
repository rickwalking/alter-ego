# AE-0525 — P3b — safe LangGraph checkpoint pruning (AE-0342 fix)

Status: Ready
Tier: T2
Priority: Medium
Type: Bug
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Fix the never-matching checkpoint TTL/prefix so old checkpoints of published/rejected projects are pruned, with safety rails because deletion is irreversible.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → validation on the
disposable droplet → AE-0522 (live on merge) → AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- Root-cause the never-matching prefix (AE-0342); dry-run count of matched threads; Pedro signs off on the matched set; backup the checkpoint tables; then delete; never touch projects that may need republish/rework.

## Non-Goals

- Any change to the queue or the daily scan.

## Acceptance Criteria

- [ ] AC1 Given a dry run, Then it lists the matched thread ids and their projects' states and deletes nothing.
- [ ] AC2 Given Pedro's sign-off and a backup, When the prune runs, Then only the signed-off threads are deleted and the checkpoint table shrinks accordingly.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
