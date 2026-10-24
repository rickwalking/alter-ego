# AE-0545 — move Langfuse off the droplet to Langfuse Cloud (replaces the AE-0544 1280M fix-forward)

Status: In Development
Tier: T1
Priority: Critical
Type: Bug
Area: Infra
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: fix/ae-0545-langfuse-cloud
Kanban Card: TBD
Created: 2026-10-24
Updated: 2026-10-24

## Goal

Stop running the Langfuse stack on the 3916 MiB droplet: tracing goes to Langfuse Cloud (Hobby tier), and the memory
it frees closes the budget for the P1 generation worker.

## Problem

AE-0521 (#269) capped Langfuse web at 768M with a 448 MiB Node heap; after the deploy Langfuse web crash-looped on prod
(1,050 restarts, `JavaScript heap out of memory`; RSS peak 1105 MiB) and was stopped at 11:11 UTC on 2026-10-24. A
1280M cap (AE-0544, #278) would close today's budget with ≈ 175 MiB and leave the P1 budget ≈ 330 MiB short. Pedro
decided to move Langfuse to Langfuse Cloud instead.

## Scope

- docker-compose.prod.yml: remove langfuse, langfuse-worker, langfuse-db-init, clickhouse, minio, minio-init and the
  clickhouse_data / minio_data volumes (used only by Langfuse; postgres and redis stay, the app uses them). The
  backend's `LANGFUSE_HOST` defaults to `https://cloud.langfuse.com`.
- deploy.yml: backend env from new secrets `LANGFUSE_CLOUD_PUBLIC_KEY` / `LANGFUSE_CLOUD_SECRET_KEY` and variable
  `LANGFUSE_CLOUD_HOST` (default EU); the self-hosted Langfuse secrets are no longer written or required;
  `down --remove-orphans` so the deploy removes the old Langfuse containers.
- Backend: tracing starts only with both keys; with either missing it stays off (no client, no handler) and logs
  `langfuse_disabled` once. Settings default host = Langfuse Cloud. `clickhouse-config/low-memory.xml` (prod only)
  removed; the dev compose keeps its own config.
- Tests and the AE-0521 budget report restated without Langfuse (today and after P1). The MinIO image-pin test
  (AE-0480) is retired with the service.
- Setup steps for Pedro: PR body and `~/alter-ego-qa/2026-10-22-dashboard-qa/langfuse-cloud-setup.md`.

## Non-Goals

- Migrating old self-hosted traces (not migrated). Deleting the old volumes or the `langfuse` database (Pedro, by
  hand, optional). The dev `docker-compose.yml` (keeps its local Langfuse).

## Acceptance Criteria

- [ ] AC1 Given the production compose file, Then no Langfuse, ClickHouse or MinIO service or volume remains, and
  nothing depends on them.
- [ ] AC2 Given no Langfuse keys (or only one), When the backend starts, Then tracing is off: no client, no handler,
  no export retries, one `langfuse_disabled` log line.
- [ ] AC3 Given both Cloud keys, Then the backend traces to the configured Cloud host.
- [ ] AC4 Given the deploy, Then it writes the Cloud keys and host from the new secret/variable, does not require
  them, and removes the old Langfuse containers (`--remove-orphans`).
- [ ] AC5 The budget report states today's and the post-P1 headroom with Langfuse gone.
- [ ] AC6 Pedro's setup steps (region, project, keys, GitHub secrets) are written down, noting old traces are not
  migrated.

## Gherkin

`backend/tests/features/langfuse_cloud_ae0545.feature`.

## Decision Log

- 2026-10-24 (Pedro): move Langfuse to Langfuse Cloud (Hobby tier) instead of the 1280M cap of AE-0544.
- 2026-10-24: new secret names (not the old `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`), so the self-hosted project
  keys still stored there can never be sent to Cloud (every export would be rejected).
