# AE-0544 — fix-forward: Langfuse web 1280M with a 1024 MiB heap (crash loop after AE-0521)

Status: In Development
Tier: T1
Priority: Critical
Type: Bug
Area: Infra
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: fix/ae-0544-langfuse-heap
Kanban Card: TBD
Created: 2026-10-24
Updated: 2026-10-24

## Goal

Stop the Langfuse web crash loop that the AE-0521 caps caused on prod.

## Problem

AE-0521 (#269) capped Langfuse web at 768M with `NODE_OPTIONS=--max-old-space-size=448`. After the deploy, Langfuse
web crash-looped on prod (1,050 restarts, `FATAL ERROR: Reached heap limit ... JavaScript heap out of memory`): its
working set is JavaScript heap and its RSS peaked at 1105 MiB on 2026-10-23, so a 448 MiB heap cannot hold it. The
container was stopped on prod at 11:11 UTC on 2026-10-24. Any deploy before this fix restarts the crash loop.

## Scope

- docker-compose.prod.yml: Langfuse web limit 768M → 1280M, heap 448 → 1024 MiB (Pedro, 2026-10-24).
- Compose caps test: Langfuse at 1280M, heap at least 1024 MiB and heap + 256 MiB native ≤ the cap.
- AE-0521 budget report: budget restated with Langfuse at 1280M (today and after P1); coincident-peak line fixed
  (2286 − (993 − 768) = 2061, not 2087).

## Non-Goals

- Any other cap. Langfuse worker (already 768M, not crashing).

## Acceptance Criteria

- [ ] AC1 Given the production compose file, Then Langfuse web is capped at 1280M with a Node heap of 1024 MiB, and
  the compose caps test fails on the old 448 MiB heap.
- [ ] AC2 Given the deploy, Then Langfuse web stays up (RestartCount stays 0) with no heap-OOM in its log.
- [ ] AC3 The budget report states the headroom with Langfuse at 1280M today and after P1, plainly.

## Test classification (CLAUDE.md, AE-0153)

- Behavior: production config only (container memory and Node heap); no API, UI or business-rule change.
- Tests: `backend/tests/unit/scripts_ci/test_compose_memory_caps_ae0521.py` with its feature
  `backend/tests/features/compose_memory_caps_ae0521.feature` (scenario "Langfuse web keeps its Node heap below its
  container limit" updated). Seeded check: with the old `--max-old-space-size=448` the test fails (1 failed).
- Affected gates: backend:test, backend:gherkin-refs.

## Decision Log

- 2026-10-24 (Pedro): Langfuse web memory limit 1280M, heap `--max-old-space-size=1024`.
- 2026-10-24: with Langfuse at 1280M the budget closes today with ≈ 175 MiB headroom and does NOT close after P1
  (≈ 330 MiB short); Pedro decides how P1 fits before AE-0522 goes live.
