# Checkpoint and lock_version Inventory (AE-0075)

Capture date: 2026-06-12. Evidence inputs for ADR-0009's operating-context
statement and the Phase 4+ drain-before-migrate step.

## Verdict

**Serialization: PORTABLE**

- All 6,918 checkpoints are `type=msgpack` (LangGraph `JsonPlusSerializer`;
  no custom serde configured anywhere).
- Blob scan: `rag_backend` appears in **0/6,918** checkpoint blobs and
  **0/67,705** write blobs; no `lc_serializable`/pydantic constructor
  markers found.
- A captured fixture deserializes in a subprocess that imports **no**
  `rag_backend` module (mechanically asserted via `sys.modules`), and a
  structural scan finds zero class-path entries
  (`backend/tests/unit/test_checkpoint_fixture_portability.py`).

Consequence: package moves do not strand persisted checkpoints. No
escalation fires; the finish-or-restart policy stands on convenience
grounds, not necessity.

## Checkpoint backends per environment

| Environment | Backend | Store | Contents |
|---|---|---|---|
| Dev (settings default) | `sqlite` | `backend/output/carousel_checkpoints.sqlite` | **6,918 checkpoints, 67,705 writes, 1,636 threads** |
| Dev Postgres (`rag_db`) | available option | — | **No checkpoint tables exist** (postgres backend never used) |
| Mutation-test artifact | sqlite | `backend/mutants/output/...` | test residue, not production state |
| Other options | `memory`, `disabled` | — | ephemeral / none |

Settings: `carousel_checkpoint_backend` (default `sqlite`),
`carousel_checkpoint_sqlite_path`, `carousel_checkpoint_postgres_url`,
`carousel_checkpoint_ttl_days=30` (`infrastructure/config/settings.py:74-77`).
No `CAROUSEL_CHECKPOINT_*` overrides in `.env`/`docker-compose.yml`.

Thread count (1,636) far exceeds project count (39): threads accumulate
per workflow run/retry. Thread-level state is disposable run history;
the project rows define what is worth finishing.

## Live workflows and finish cost

39 carousel projects total (`blog_posts` table is empty). Status
distribution:

| current_phase | phase_status | count | Drain disposition |
|---|---|---:|---|
| outline / content | awaiting_human | 5 + 5 | Finish cheap (one approval each) or restart |
| research | awaiting_human | 3 | Finish cheap |
| final_review | awaiting_human | 2 | Finish cheap (last gate) |
| design / images / published | awaiting_human | 1+1+1 | Finish cheap |
| images | in_progress | 1 | Let complete or restart |
| brief | pending | 4 | Restart trivially (nothing produced yet) |
| research | rejected | 6 | Terminal-ish; no drain action |
| final_review / published | approved | 6 + 4 | Effectively done; no drain action |

Owner-estimate basis: 18 awaiting-human + 1 in-progress + 4 pending ≈
**23 workflows with any finish cost, each one or two approval clicks**;
the rest are terminal or restart-trivial. A full drain before any
Phase 4+ schema migration is realistically **under an hour** of owner
time, or zero if restart-preferred is applied to the stale ones.

## lock_version findings

Distributions (query text as run):

```sql
SELECT lock_version, count(*) FROM carousel_projects GROUP BY 1 ORDER BY 1;
-- 1:23, 2:4, 3:3, 4:1, 5:1, 7:2, 9:2, 13:1, 16:1, 18:1  (39 rows)
SELECT lock_version, count(*) FROM blog_posts GROUP BY 1 ORDER BY 1;
-- (no rows; table empty)
```

**Correction to the plan's verification record:** the claim that "no
application code enforces `lock_version`" is **wrong**.
`application/services/optimistic_lock_service.py` performs atomic
compare-and-increment for both tables, and the varied values (up to 18)
prove active use. Coverage is **partial**: callers are
`api/routes/workflow_audit.py`, `api/routes/blog_post.py`, and
`api/routes/carousels/editorial_workflow_routes_validate.py` — other
write paths (workflow workers, remaining carousel routes) bypass it.

Consequence for Phase 2.5: the `lock_version` item shrinks from
"implement enforcement from scratch" to "**extend existing
`optimistic_lock_service` coverage to all write paths and add the
AE-0073 conflict-contract tests**".

## Fixture provenance

`backend/tests/fixtures/checkpoints/carousel_checkpoint.msgpack.bin` —
latest checkpoint from the dev sqlite store, re-encoded after
sanitization (strings >40 chars replaced with `REDACTED-<len>-CHARS`,
structure and types preserved); metadata in the sibling `.meta.json`.
Manual scan: no emails, URLs, credentials, or key material in the blob.
