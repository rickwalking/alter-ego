---
status: accepted
date: 2026-10-26
decision-makers: Pedro Marins
consulted: architecture research
informed: delivery team
---

# ADR-0028: Persist a sanitized carousel generation event log

## Context and Problem Statement

Pedro needs to inspect what happened during carousel creation on the carousel page while Langfuse is disabled. `generation_runs` contains only current queue state and counters. Workflow audit/outbox records lack generation-run correlation and phase-attempt timings, and existing payloads/logs can contain prompts, feedback, model output, raw exceptions, SQL or file data. None is a safe complete timeline.

## Decision Drivers

- Useful run, phase, image, export, retry and recovery diagnostics without Langfuse.
- No persisted secrets, prompts, personal content, SQL parameters or image bytes.
- No meaningful generation latency, worker memory growth or new failure mode.
- Owner/admin authorization, bounded reads and 30-day retention.
- Existing PostgreSQL, daily purge and deploy one-shot; no new service or scheduler.

## Considered Options

1. Reconstruct the timeline from existing runs, audit/outbox rows and structured logs.
2. Capture scoped structlog output and asynchronously batch it into a new table.
3. Explicitly record allowlisted events into `carousel_generation_events` through independent short transactions.

## Decision Outcome

Chosen option 3 (Pedro, 2026-10-26). A new append-only table stores bounded diagnostic events with run/carousel foreign keys, timestamps, phase, outcome, duration, attempt, classified codes and optional Langfuse trace identity. Flat JSON details are allowlisted and capped at 4096 serialized bytes. Raw exception messages and generation content are never accepted.

A run-scoped context carries only identity and a stateless recorder. Each event is sanitized and inserted immediately in its own transaction with a 100 ms timeout. Errors produce a content-free warning and are swallowed; no events are buffered across steps/runs and no background queue is added. Queue state remains authoritative under ADR-0026.

The owner/admin API keyset-paginates at most 200 events. The workspace groups runs and phases and refreshes through existing workflow SSE/poll updates. The daily recovery purge removes events older than 30 days. Alembic and the existing idempotent generation-queue schema one-shot deliver the table and indexes.

Option 1 cannot reconstruct phase durations and would expose unsafe payloads. Option 2 risks unbounded pending tasks/memory and cannot reliably await database writes from synchronous logging processors.

### Consequences

- Good: useful timeline without Langfuse; explicit privacy boundary; bounded reads/writes; no new runtime service.
- Good: optional real trace id and SDK-generated trace URL improve diagnostics when Langfuse returns.
- Bad: explicit instrumentation must be maintained at generation seams; independent writes can miss an event during a crash or store outage.
- Neutral: the event table is derivative, expires after 30 days and is not an audit replay or queue-recovery source.

## Validation

- Planted-secret and DBAPIError tests inspect stored rows and API output.
- Store exceptions/timeouts leave generation outcomes unchanged; insert overhead is measured.
- Owner/admin/reviewer/anonymous and cross-project API tests prove access boundaries.
- PostgreSQL migration, one-shot, cascade, cursor and daily-purge tests pass.
- React tests prove grouping, accessible controls, live invalidation without a new timer and PT/EN rendering.
