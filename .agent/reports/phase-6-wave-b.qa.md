# QA Report — Phase 6 Wave B (AE-0127 + AE-0130)

**Verdict: PASS** — converged over 3 external-QA rounds (FAIL → PASS → PASS; two consecutive passing
rounds on the final code). Gate spine **14 PASS / 0 FAIL / 3 SKIP** (test/diff-cover/migrations SKIP locally
without DATABASE_URL → run in CI); `check-integrity` 0 blockers; mutation PASS; no suppressions, no
`.importlinter` edits, no per-file-ignore/threshold changes.

## Scope
- **AE-0127** — `BlogPost.origin` field + additive backfill migration `b2c3d4e5f6a7` (no destructive drops).
- **AE-0130** — transactional outbox `event_outbox` (migration `c3d4e5f6a7b8`); single durable publish path.

Migration chain linear, single head `c3d4e5f6a7b8`; fresh-DB upgrade + full downgrade verified on SQLite.

## Round 1 — FAIL → fixed
- **CRITICAL (migration data loss).** `downgrade()` deleted ALL `origin='carousel'` project-linked rows,
  destroying pre-existing posts that step 2 only re-labelled. **Fix:** downgrade DELETE restricted to the
  step-3 backfill inserts via `slug LIKE 'carousel-%'`; dropping the column reverts the re-label without data
  loss. New alembic upgrade/downgrade regression test proves pre-existing rows survive.
- **HIGH (payload byte-identity).** Relay rebuilt the event timestamp from a DB `created_at` round-trip
  (SQLite returns naive → no `+00:00`), so payloads were not byte-identical to the legacy
  `datetime.now(UTC).isoformat()` path. **Fix:** new `event_timestamp` column stores the exact ISO string at
  emit; the relay publishes it verbatim (dialect-proof). `created_at` is ordering-only.
- **MEDIUM** ×3 + **LOW** ×2: `FOR UPDATE SKIP LOCKED` claim (no concurrent double-delivery), drain loop in
  `relay_after_commit` (multi-batch backlog), integration test of the real commit→after_commit→fresh-session
  relay + rollback-no-stale path, `_coerce_origin` edge tests, `attempts server_default='0'`.

## Round 2 — PASS
4 LOW findings, all acceptable/documented. Two actionable closed: documented the `carousel-%` discriminator
collision assumption (negligible, accepted); added drain-loop termination unit tests (drains past a full
batch; stops on a zero-progress all-failed batch — no spin).

## Round 3 — PASS
4 LOW findings, all acceptable (SKIP LOCKED no-op on SQLite — by design/documented; at-least-once redelivery
on crash — by design; same-package constant import — acceptable). Migration-test Gherkin reference corrected
to "not applicable (schema migration)".

## Evidence
- 37 targeted tests green (relay, event-service, publishing module, after-commit integration, migration
  upgrade/downgrade regression). mypy clean (493 files), ruff clean, vulture clean, lint-imports 19/0.
- Behavior-preserving: additive-only, no destructive DDL, event payloads byte-identical, single durable path.
