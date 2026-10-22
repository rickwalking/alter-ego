# AE-0521 — P5 — memory reservations and limits for the web tier

Status: Ready
Tier: T2
Priority: High
Type: Infra
Area: Infra
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Cap the currently unbounded containers (backend, frontend, langfuse, postgres) so a generation worker can never push the kernel OOM killer onto the website; precondition for enabling the queue.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → AE-0522 (flag off) → validation → flag on →
AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- Measure each container's RSS over a normal day (from AE-0520) and set `mem_limit` = measured peak + 30 %, plus reservations for backend/frontend/nginx.
- Apply one service per deploy; revert by removing the limit if a container is OOM-killed (documented rollback).
- If the box budget does not close, propose to Pedro shrinking the observability stack (ClickHouse/Langfuse caps or Langfuse off-box) or a bigger droplet.

## Non-Goals

- No change to the generation code path. No droplet resize without Pedro's decision.

## Acceptance Criteria

- [ ] AC1 Given the new limits, When a normal day runs, Then no container is OOM-killed and web p95 stays within 20 % of the AE-0520 baseline.
- [ ] AC2 The box memory budget (Σ limits + worker peak ≤ RAM with headroom) is written down and closes, or Pedro's decision on the alternative is recorded.
- [ ] AC3 The rollback for each cap is documented and tested on the disposable droplet.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
