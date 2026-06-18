# One-Time Prod DB Reconcile to Alembic (AE-0207)

**Audience:** operator (human) with SSH access to the DigitalOcean prod droplet.
**Run:** exactly **once**, **before** the first deploy that ships the
migrate-on-deploy change (ADR-012). After this, every deploy runs
`alembic upgrade head` + the drift gate automatically — you never repeat these
steps.

> ⚠️ This touches the **live prod database**. CI does **not** and **must not** run
> it. Take a backup first. Read every step before running anything.

## Why this is needed

Prod was bootstrapped with SQLAlchemy `create_all` and has **no `alembic_version`
table** — Alembic has never run there. The migration chain is self-contained
(AE-0086): baseline `63eaefa67b8c` → `a1b2c3d4e5f6` → `b2c3d4e5f6a7` →
`c3d4e5f6a7b8` → `d4e5f6a7b8c9` → `e5f6a7b8c9d0` (head).

Because `create_all` already built most of the current schema (plus two columns
hand-patched on the server: `caption_en`, and `blog_posts.origin` /
`blog_posts.distribution`), we must tell Alembic which revision the live schema
**already matches** (`stamp`), then let it apply only what is genuinely missing
(`upgrade`). Running a bare `upgrade head` against an unstamped prod would try to
re-add columns that already exist and fail.

## Step 0 — Backup (mandatory)

```bash
ssh "$DO_USER@$DO_HOST"
cd /opt/alter-ego
# Dump the prod DB to a timestamped file OUTSIDE the container.
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  > "/opt/alter-ego/backups/prod-$(date +%Y%m%d-%H%M%S).sql"
```

Keep this dump. If anything below goes wrong, restore from it before retrying.

## Step 1 — Confirm there is no `alembic_version` yet

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT to_regclass('public.alembic_version');"
```

- `(null)` → never stamped; continue to Step 2 (the normal case).
- a table name → prod is **already** stamped; **stop**. The one-time reconcile was
  already done; skip straight to deploying normally.

## Step 2 — Decide the stamp target

The live prod schema must be compared to the ORM. Run the drift checker (it reads
`information_schema` and reports any mapped column the live DB lacks). Inside the
**backend** container, the venv is on `PATH` and `DATABASE_URL` is already set:

```bash
docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
  python -m rag_backend.infrastructure.database.check_drift_cli
```

Interpret the output:

- **`OK: live schema matches all mapped ORM columns.`**
  The live schema already equals **head**. Stamp head and you are done:
  ```bash
  docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
    alembic stamp head
  ```
  Go to Step 4.

- **Drift reported (some columns/tables missing).**
  The live schema sits **behind** head. Stamp the **baseline** (the schema
  `create_all` reliably produced), then let Alembic apply only the missing
  forward migrations:
  ```bash
  # 1) Adopt the baseline as the current revision WITHOUT running its DDL.
  docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
    alembic stamp 63eaefa67b8c

  # 2) Apply the remaining migrations. Additive column migrations are written to
  #    be safe to apply; if a specific migration fails because that object was
  #    ALREADY hand-patched onto prod (e.g. blog_posts.origin / distribution),
  #    stamp PAST just that one revision and continue — see Step 3.
  docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
    alembic upgrade head
  ```

## Step 3 — Handle a migration whose object already exists (only if upgrade fails)

If `upgrade head` fails on a migration whose column/table prod **already has**
(the hand-patched `blog_posts.origin` / `caption_en` / `distribution`, or an
`event_outbox` table that create_all already made), do **not** edit the migration.
Stamp exactly that one revision (marking it applied without running its DDL), then
resume the upgrade:

```bash
# Replace <rev> with the revision id from the alembic error (e.g. b2c3d4e5f6a7
# for origin, or e5f6a7b8c9d0 for distribution).
docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
  alembic stamp <rev>
docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
  alembic upgrade head
```

Repeat per offending revision until `upgrade head` completes. Revision order:
`63eaefa67b8c` → `a1b2c3d4e5f6` → `b2c3d4e5f6a7` → `c3d4e5f6a7b8` →
`d4e5f6a7b8c9` → `e5f6a7b8c9d0`.

## Step 4 — Verify

```bash
# alembic_version now holds the head revision.
docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
  alembic current

# The drift gate must now pass (this is the same check the deploy runs).
docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
  python -m rag_backend.infrastructure.database.check_drift_cli
# Expect: "OK: live schema matches all mapped ORM columns."
```

Both must succeed. If the drift check still reports a missing column, a migration
for it is missing from the chain — author it (do **not** hand-`ALTER` prod again);
that recurrence is exactly what this work eliminates.

## After this

Nothing further is manual. Every subsequent deploy (`deploy.yml`) runs
`alembic upgrade head` and the drift check automatically, before the app serves
traffic, and aborts the deploy if either fails (ADR-012).
