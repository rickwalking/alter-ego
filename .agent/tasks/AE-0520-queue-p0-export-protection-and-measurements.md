# AE-0520 — P0 — export protection and measurements (no queue)

Status: Ready
Tier: T2
Priority: High
Type: Feature
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: feat/ae-0520-queue-p0 (code, PR #247); docs/ae-0520-measurements (report)
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Protect the website from today's carousel generation load and collect the measurements that gate ADR-0026, with no queue and no schema change except one index.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → AE-0522 (flag off) → validation → flag on →
AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- Global export lock: a Postgres advisory lock around `export_slides`, PT/EN and standard/HD exports run one after another; Chromium flags `--disable-dev-shm-usage`, `--renderer-process-limit=1`.
- CPU-heavy steps off the event loop: `_crop_border_artifact`, `PdfSlideBuilder.build`, PIL validations via `asyncio.to_thread`.
- Staggered autopilot starts: at least 20 minutes between `queued → generating` transitions.
- Deploy one-shot: `CREATE INDEX CONCURRENTLY IF NOT EXISTS` on `carousel_projects(phase_status, current_phase)`.
- Measurements written to `.agent/reports/AE-0520.measurements.md` (exit criteria in the plan §5 P0): carousel run RSS with and without HD @2x and the HD decision for autopilot (proposal to Pedro); box memory budget; root cause of the 10-21 / 10-22 `escalated / run_stale` runs; side-effect inventory of graph nodes with their idempotency; off-box web p95 baseline; Postgres connection headroom.

## Non-Goals

- No queue, worker or new table (AE-0522). No memory caps on containers (AE-0521).

## Acceptance Criteria

- [x] AC1 Given two carousels reach export at the same time, When both export, Then only one Chromium export runs at a time (test with two concurrent exports).
- [x] AC2 Given an export runs, When a web request arrives, Then the event loop is not blocked by PIL/img2pdf work (test asserts those calls run in a thread).
- [x] AC3 Given three runs are queued at 11:05, When the runner steps, Then generation starts are at least 20 minutes apart.
- [x] AC4 Given the deploy one-shot runs twice, When it finishes, Then the index exists once and the second run is a no-op.
- [ ] AC5 The measurements report exists with all six exit criteria answered (or marked blocked with the reason).

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
- 2026-10-22: AC1–AC4 in PR #247. AC5 stays open: `.agent/reports/AE-0520.measurements.md` answers criteria 3–6;
  criterion 1 (run RSS with/without HD) and the box budget (criterion 2) wait for the run peak of the next real
  run, and the HD and budget decisions stay with Pedro.
