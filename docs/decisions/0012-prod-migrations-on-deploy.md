# ADR-012: Production uses Alembic Migrations on Deploy (no `create_all`)

## Status

Accepted

## Context

Production was bootstrapped with SQLAlchemy `create_all`
(`infrastructure/database/config.py` `init_db`) and has **no `alembic_version`
table** — Alembic never ran there. `deploy.yml` only ran
`docker compose up -d --build`; no `alembic upgrade`.

`create_all` creates *missing tables* but **never `ALTER`s an existing one**. So
every column added to an ORM model after its table already existed silently 500'd
production the first time it was referenced — the table was already present, so
`create_all` did nothing, and the new column simply did not exist in the live
schema. This is not hypothetical: it hit prod **twice** —
`carousel_projects.caption_en` (2026-06-13) and `blog_posts.origin` +
`blog_posts.distribution` (2026-06-18, hot-patched by hand on the server).

A Kaizen prod sweep (`.agent/reports/kaizen-prod-2026-06-18.plan.md`, validated by
an independent architect cold-critic review) flagged this as the single biggest
production-readiness gap. The migration chain was made self-contained in **AE-0086**
(7 versions under `backend/alembic/versions/`, baseline `63eaefa67b8c`), which
unblocks running migrations on deploy.

How a database moves to the target schema is architecturally significant
(per CLAUDE.md and ADR-009), so it requires an ADR.

## Decision

**Production reaches its target schema exclusively via Alembic migrations, run on
every deploy. `create_all` is no longer the prod schema authority, and a
schema-vs-models drift gate fails any deploy whose live schema is missing a mapped
ORM column.**

1. **Migrate on deploy.** `deploy.yml` brings up Postgres, then runs
   `alembic upgrade head` (and the drift check below) via a one-shot
   `docker compose run --rm --no-deps backend ...` **before** the application
   containers serve traffic. `set -e` aborts the deploy if either step fails, so a
   broken or missing migration never reaches a live app.

2. **Drift gate (the exact-class detector).** A reusable check
   (`infrastructure/database/schema_drift.py` + `check_drift_cli.py`) compares the
   mapped `Base.metadata` columns against what the live database actually reports
   via `information_schema.columns`, and **fails when a mapped column is absent**.
   This is precisely the class that 500'd prod (a model column with no migration,
   or a migration not applied). It is wired:
   - as the `schema-drift` backend gate in `scripts/ci/gates.sh` (Postgres-
     dependent: `SKIP` locally without `DATABASE_URL`, runs in CI), and
   - as a deploy step immediately after `alembic upgrade head`.

3. **`create_all` stays for local/test bootstrap only.** `init_db` keeps using
   `create_all` for the dev compose stack and the in-memory test DB — those are
   ephemeral and rebuilt from scratch, so the "never ALTERs" hazard does not apply.
   Prod (and staging) gain migration-on-deploy; they are never schema-authored by
   `create_all`.

4. **One-time prod reconcile (operator runbook, not automated).** The existing
   drifted prod DB has no `alembic_version`. Before the first migrated deploy an
   operator runs a one-time `alembic stamp <baseline>` + reconcile so Alembic
   adopts the live schema as its starting point. The exact, copy-pasteable steps
   live in `docs/deployment/prod-migration-reconcile.md`. This is deliberately a
   manual, audited operator action — it touches prod data and must not run
   automatically from CI.

## Consequences

**Good:**

- New model columns ship to prod through a migration; they can no longer silently
  500 on first reference.
- The drift gate catches the failure class deterministically in CI and on deploy,
  not in production after the fact.
- Schema history is explicit and reversible (Alembic chain), not implicitly
  reconstructed by `create_all`.

**Bad:**

- Every prod-affecting model change now **requires** an Alembic migration — there
  is no `create_all` fallback on prod. (This is the intended constraint.)
- The one-time reconcile is a manual operator step; if skipped, the first migrated
  deploy fails fast at `alembic upgrade head` (safe, but blocks the deploy until
  the operator runs the runbook).
- The drift gate and deploy migration step depend on a reachable Postgres; the
  gate is inconclusive (`SKIP`) where no DB is available locally.

## Alternatives Considered

| Option | Why Rejected |
|--------|--------------|
| Keep `create_all` on prod | The root cause — it never `ALTER`s existing tables; columns silently 500. |
| `create_all` + ad-hoc manual `ALTER` on the server | Exactly what happened twice; unaudited, error-prone, no history, no gate. |
| Drift check only (no migrate-on-deploy) | Detects drift but never fixes it; deploys would just fail until someone migrates by hand. |
| Run migrations from app startup (`init_db`) | Multiple app replicas race the migration; couples app boot to DDL; harder to gate before traffic. |

## Related Decisions

- ADR-009: Adopt Domain Modular Monolith (schema ownership is significant)
- ADR-011: Canonical Distribution Home (the `distribution` column that 500'd prod)

## Tags

#deployment #database #migrations #devops #reliability
