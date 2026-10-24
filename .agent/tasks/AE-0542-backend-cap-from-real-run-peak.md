# AE-0542 — backend and P1 worker memory caps from the real prod run peak (AE-0521 follow-up)

Status: In Development
Tier: T1
Priority: High
Type: Infra
Area: Infra
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: feat/ae-0542-run-peak-caps
Kanban Card: TBD
Created: 2026-10-24
Updated: 2026-10-24

## Goal

Size the backend memory cap (and the planned P1 worker cap) from the first carousel run sampled on prod, as Pedro
asked when AE-0521 shipped on the off-box estimate.

## Problem

AE-0521 capped the backend at 1344M from an off-box HD export (≈ 1011 MiB estimated run peak). The first prod run
sampled (carousel 5350e0ca, 2026-10-24 00:52–02:07 UTC, five export rounds) peaked at 1181 MiB during HD exports:
under the cap, but only 163 MiB (14 %) below it, short of the peak + 30 % rule. The AE-0521 budget report also had
an arithmetic slip in the coincident peak with Langfuse capped (2087 instead of 2286 − (993 − 768) = 2061).

## Scope

- docker-compose.prod.yml: backend limit 1344M → 1536M (1181 + 30 %), reservation unchanged (384M).
- `test_compose_memory_caps_ae0521.py`: the measured run peak constant becomes the prod value (1181).
- AE-0520 measurements: criterion 1 answered with the run numbers. AE-0521 budget report: run peak section, the
  2061 fix, budgets today and after P1. AE-0522 ticket and the AE-0517 plan: worker cap 1536M, backend 512M after P1.

## Non-Goals

- Any other cap. Any code change.

## Acceptance Criteria

- [ ] AC1 Given the new backend limit, Then it is at least the prod run peak (1181 MiB) + 30 %, asserted by the compose
  caps test.
- [ ] AC2 AE-0520 criterion 1 is recorded with the run's peaks (with and without HD), and the budget is restated from
  them (today and after P1).
- [ ] AC3 The P1 worker cap in AE-0522 and the plan matches the prod peak + 30 %.

## Test classification (CLAUDE.md, AE-0153)

- No public or user-visible behavior change: a container memory limit value and documents only.
- Unit test path: `backend/tests/unit/scripts_ci/test_compose_memory_caps_ae0521.py` (feature
  `backend/tests/features/compose_memory_caps_ae0521.feature`) asserts the limit against the measured peak; its seeded
  case (`test_a_service_without_a_memory_limit_is_reported`) proves the check fires.
- Affected gates: backend:test, backend:gherkin-refs, backend:diff-cover (no Python source changed).
- Reviewer/QA sign-off on the no-`.feature` classification: requested in the PR.

## Decision Log

- 2026-10-23 (Pedro): ship AE-0521 on the off-box estimate and adjust in a follow-up if the real peak differs.
- 2026-10-24: the real peak (1181 MiB) is above the estimate (1011 MiB): backend and P1 worker caps 1536M.
