# Carousel Workflow — Scaled-Down Rollback Drill

**Status:** Active evidence
**Ticket:** AE-0113 (Phase-4 exit-gate evidence; blocks AE-0107)
**Authority:** [ADR-0009 §2 "Phase 2.5 exit-gate parameterization"](../decisions/0009-adopt-domain-modular-monolith.md), §7 "Rollback and forward-fix policy"
**Related:** [`carousel-project-field-ownership.md`](./carousel-project-field-ownership.md)

## 1. Scope — explicitly scaled-down

This drill is the **scaled-down rollback drill** required by ADR-0009 before any
carousel write path is redirected (AE-0107). Per ADR-0009 §2 and §7, the
scaled-down + migrate-in-place track satisfies "test rollback with
production-shaped data" with:

- a **database restore drill**, plus
- a **trace-correlated smoke comparison** (legacy state + workflow trace vs.
  post-restore state).

**Out of scope (deliberately, per ADR-0009 §2 — NOT a gap):**

- ❌ Full production-traffic rollback drill
- ❌ Mixed-version / dual-running tests
- ❌ Parity alerting on live traffic
- ❌ Cross-version checkpoint migration tooling (finish-or-restart policy
  applies instead — see §4)

This document records the drill procedure and its **invariants**. The
automatable parts are implemented and CI-runnable; the live-PostgreSQL restore
step is documented for an operator/CI job because CI has no live Postgres (see
the env note in the project memory: "CI has no external API keys"; the same
constraint applies to a live DB).

## 2. What the drill protects

The rollback unit is the carousel workflow's **persisted state** and its
**trace-correlated audit history**:

| Concern | Rollback-critical artifact |
|---|---|
| Workflow row state | `carousel_projects.workflow_status`, `phase_status`, `phase_progress`, `lock_version` |
| Workflow trace | `workflow_audit_log` rows keyed by `aggregate_id` (= project id), `aggregate_type = "project"`, ordered by `version` |
| Checkpoints | LangGraph checkpoints (finish-or-restart, not migrated — §4) |

The drill invariant (ADR-0009 §7, "executable compatibility test"):

> After a database restore, the carousel workflow state **and** its
> trace-correlated audit-event sequence MUST be **byte-identical** to the
> pre-change baseline. Any divergence is a rollback-correctness failure.

## 3. Procedure

### 3.1 Automated (CI-runnable today)

The snapshot + comparison logic lives in
[`backend/scripts/carousel_rollback_drill.py`](../../backend/scripts/carousel_rollback_drill.py):

- `snapshot_carousel_state(db, project_id)` — captures the rollback-critical
  row fields and the ordered audit trace into an immutable
  `CarouselStateSnapshot`.
- `compare_snapshots(baseline, restored)` — deterministic, field-by-field +
  trace-by-trace comparison returning `SnapshotComparison(matched, differences)`.

The smoke comparison is exercised end-to-end by
[`backend/tests/integration/test_carousel_rollback_smoke.py`](../../backend/tests/integration/test_carousel_rollback_smoke.py)
against in-memory SQLite (same harness as the rest of `tests/integration`). It
asserts both that a complete restore matches the baseline **and** that an
incomplete restore (residual drift / dropped row) is detected — proving the
comparison has teeth.

```bash
cd backend
uv run pytest tests/integration/test_carousel_rollback_smoke.py -q
```

### 3.2 Operator / CI-with-Postgres steps (documented; live DB required)

Run against a staging or production-shaped snapshot — never live production
traffic.

1. **Pick a target project** with workflow history (`workflow_audit_log` rows).
2. **Capture baseline backup** before any change:
   ```bash
   pg_dump --format=custom --file=carousel_baseline.dump "$DATABASE_URL"
   ```
3. **Capture baseline snapshot** (in-process, using the helper) and persist it
   as the comparison oracle:
   ```python
   from scripts.carousel_rollback_drill import snapshot_carousel_state
   baseline = await snapshot_carousel_state(db, project_id)
   ```
4. **Apply the forward change** under test (the migration / write-path
   redirection being de-risked).
5. **Restore** from the baseline backup:
   ```bash
   pg_restore --clean --if-exists --dbname="$DATABASE_URL" carousel_baseline.dump
   ```
6. **Re-snapshot and compare:**
   ```python
   restored = await snapshot_carousel_state(db, project_id)
   result = compare_snapshots(baseline, restored)
   assert result.matched, result.differences
   ```

### 3.3 Drain-before-migrate precondition (ADR-0009 §2)

Before any schema-modifying migration, every live checkpoint from the Phase-2.5
inventory MUST be **finished on pre-migration code** or **restarted with
documented owner consent**. No schema migration runs while a checkpoint
references the old shape. This drill does not build cross-version checkpoint
replay (explicitly deleted from scope — ADR-0009 §4).

## 4. Side-effect & compatibility ledger (ADR-0009 §7)

| Concern | Decision for this drill |
|---|---|
| Database writes | Restored from backup; old code reads the restored rows unchanged (no schema change in the behavior-preserving Phase 4). |
| Outbox events | Not implemented before Phase 6 (ADR-0009 §8); N/A for this drill. |
| Projections | Editorial-operations views are event-built; rebuild from restored `workflow_audit_log`. |
| External publication | None triggered by the drill (no real publish; LLM/image/Pinecone never invoked). |
| Artifact builds | Not mutated; artifact URLs stay byte-identical (behavior-preserving Phase 4). |
| Checkpoints | Finish-or-restart; no cross-version replay tooling. |
| Feature flags | `editorial_workflow` flag gates the HTTP entry point; default-on in tests. |

## 5. Authorization parity (companion evidence)

The other half of the Phase-4 exit-gate evidence — three-entry-point
authorization contract tests (HTTP, agent-tool, worker) over the carousel
workflow write paths — lives in
[`backend/tests/integration/test_carousel_write_path_authz.py`](../../backend/tests/integration/test_carousel_write_path_authz.py).
It asserts the same allow/deny outcome (unauthorized denied, non-owner denied,
owner allowed) at every entry point, per ADR-0009 §5 ("HTTP routes, agent
tools, workers, and event consumers SHALL call the same context-owned policy").

## 6. Exit-gate citation

This document plus the two integration test files constitute the complete,
citable Phase-4 exit-gate rollback + authorization evidence required by
ADR-0009 §2 before AE-0107 redirects any carousel write path.
