# Carousel Checkpoint Prune (signed-off, keep-latest)

**Audience:** operator with SSH access to the prod droplet. **Run:** by hand, only after Pedro signs off the
thread list. It is not scheduled.

The LangGraph checkpoint tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`) keep every step of every
carousel. The prune deletes the old steps of finished carousels and keeps each thread's latest checkpoint (per
namespace, so subgraphs too), so a pruned carousel still opens and a parked one still resumes.

A thread is listed only when its carousel is `completed` or `failed`, was last updated before
`CAROUSEL_CHECKPOINT_TTL_DAYS` (30), is not running, has no pending republish, has no autopilot run other than
`published`, `rejected` or `expired`, and was rejected or published. Threads with no carousel project are never listed.

All safety files live in **`/app/output/checkpoint-prune/`** inside the backend container: the `carousel_output`
volume, so they survive a container restart or redeploy (`/tmp` does not). It is outside `/app/output/carousels`,
which is the only part the app serves.

```bash
ssh "$DO_USER@$DO_HOST"
cd /opt/alter-ego
docker compose -f docker-compose.prod.yml exec -T backend mkdir -p -m 700 /app/output/checkpoint-prune
```

## Step 1 — Dry run (deletes nothing)

```bash
docker compose -f docker-compose.prod.yml exec -T backend \
  python -m rag_backend.scripts.checkpoint_prune \
  --write-threads /app/output/checkpoint-prune/threads.txt
docker compose -f docker-compose.prod.yml cp backend:/app/output/checkpoint-prune/threads.txt ./threads.txt
```

One line per thread: project status, phase status, workflow status, public, archived, last update, and the
checkpoints / writes / blobs it would lose.

## Step 2 — Sign-off

Pedro reviews the list. Remove every thread he does not approve from `threads.txt`, then copy it back:

```bash
docker compose -f docker-compose.prod.yml cp ./threads.txt backend:/app/output/checkpoint-prune/threads.txt
```

## Step 3 — pg_dump of the checkpoint tables (custom format)

```bash
STAMP=$(date +%Y%m%d-%H%M%S)
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -Fc -U "$POSTGRES_USER" -t checkpoints -t checkpoint_writes -t checkpoint_blobs "$POSTGRES_DB" \
  > "/opt/alter-ego/backups/checkpoints-$STAMP.dump"
docker compose -f docker-compose.prod.yml cp "/opt/alter-ego/backups/checkpoints-$STAMP.dump" \
  backend:/app/output/checkpoint-prune/checkpoints.dump
```

Keep the host copy in `/opt/alter-ego/backups/`. It is the full restore point:
`pg_restore --clean -t checkpoints -t checkpoint_writes -t checkpoint_blobs -d "$POSTGRES_DB"`.

## Step 4 — Apply

```bash
docker compose -f docker-compose.prod.yml exec -T backend \
  python -m rag_backend.scripts.checkpoint_prune --apply \
  --threads /app/output/checkpoint-prune/threads.txt \
  --pg-dump /app/output/checkpoint-prune/checkpoints.dump
```

Before touching a row, the run refuses (exit 1) when:
- the carousel graph or one of its subgraphs keeps a LangGraph `DeltaChannel` (its value is rebuilt from the history
  this prune deletes);
- `pg_restore --list` cannot read the `--pg-dump` archive, or it holds no data for one of the three tables;
- a signed-off thread is no longer eligible (re-checked under a row lock).

It then writes every row it deletes to a new owner-only JSONL file,
`/app/output/checkpoint-prune/checkpoint-prune-<UTC stamp>.jsonl` (or `--backup PATH`, which must not exist), checks
the count, and deletes in the same transaction. A run that deletes nothing, or fewer rows than expected, exits 1 and
rolls back; its JSONL file then lists rows that are still in the tables, so move it aside before the next run. Exit 2
is a usage error (missing or existing files, `--ttl-days` below 1).

Copy the JSONL off the server too:

```bash
docker compose -f docker-compose.prod.yml cp backend:/app/output/checkpoint-prune/. ./backups/checkpoint-prune/
```

## Undo (only if needed)

The JSONL restores exactly the deleted rows, all or nothing:

```bash
docker compose -f docker-compose.prod.yml exec -T backend \
  python -m rag_backend.scripts.checkpoint_prune \
  --restore /app/output/checkpoint-prune/checkpoint-prune-<UTC stamp>.jsonl
```

## Step 5 — Reclaim the space

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "VACUUM (ANALYZE) checkpoints, checkpoint_writes, checkpoint_blobs;"
```

`VACUUM FULL` returns the space to the disk but locks the tables; run it only outside carousel activity.
