# AE-0521 — P5 — memory reservations and limits for the web tier

Status: In Development
Tier: T2
Priority: High
Type: Infra
Area: Infra
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: feat/ae-0521-memory-caps
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-23

## Goal

Cap the currently unbounded containers (backend, frontend, langfuse, postgres) so a generation worker can never push the kernel OOM killer onto the website; precondition for enabling the queue.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → validation on the
disposable droplet → AE-0522 (live on merge) → AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- Measure each container's RSS over a normal day (from AE-0520) and set `mem_limit` = measured peak + 30 %, plus reservations for backend/frontend/nginx.
- Apply one service per deploy; revert by removing the limit if a container is OOM-killed (documented rollback).
- If the box budget does not close, propose to Pedro shrinking the observability stack (ClickHouse/Langfuse caps or Langfuse off-box) or a bigger droplet.

## Non-Goals

- No change to the generation code path. No droplet resize without Pedro's decision.

## Acceptance Criteria

- [ ] AC1 Given the new limits, When a normal day runs, Then no container is OOM-killed and web p95 stays within 20 % of the AE-0520 baseline.
- [x] AC2 The box memory budget (Σ limits + worker peak ≤ RAM with headroom) is written down and closes, or Pedro's decision on the alternative is recorded.
- [ ] AC3 The rollback for each cap is documented and tested on the disposable droplet.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
- 2026-10-23 (Pedro, from the AE-0520 measurements): make room for the generation worker by shrinking the
  observability stack: lower ClickHouse's memory settings and cap Langfuse web at 768 MiB. No droplet resize,
  nothing moved off the box.
- 2026-10-23 (Pedro): keep HD exports in autopilot: all 4 renders per run (PT/EN, standard/HD), one at a time
  behind the AE-0520 export lock. The backend cap is sized for the HD export peak.
- 2026-10-23: no prod run generated in the sampling window, so the backend cap (1344M) is sized from the latest real
  HD carousel rendered off-box by the production export code (≈ 1011 MiB run peak + 30 %); AE-0520 criterion 1 stays
  pending until a prod run is sampled. All caps ship in one change (one PR), each with its own rollback
  (`.agent/reports/AE-0521.memory-budget.md`). Budget re-done with dockerd at 117 MiB after Pedro's restart.
- 2026-10-23 (Pedro): open the PR on the off-box measurement, criterion 1 pending, adjust in a follow-up if the real
  peak differs. Worker 1344M and backend 512M once generation leaves the backend (AE-0522); until then the backend
  keeps 1344M because it still runs the HD exports.
- 2026-10-24: the first prod run sampled (carousel 5350e0ca) peaked at 1181 MiB, so AE-0542 raises the backend cap
  to 1536M and the P1 worker cap to 1536M.
