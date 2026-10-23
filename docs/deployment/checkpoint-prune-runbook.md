# Carousel Checkpoint Prune (signed-off, keep-latest)

**Audience:** operator with SSH access to the prod droplet. **Run:** by hand, only after Pedro signs off the
thread list. It is not scheduled.

The LangGraph checkpoint tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`) keep every step of every
carousel. The prune deletes the old steps of finished carousels and keeps each thread's latest checkpoint, so a
pruned carousel still opens and a parked one still resumes.

A thread is listed only when its carousel is `completed` or `failed`, was last updated before
`CAROUSEL_CHECKPOINT_TTL_DAYS` (30), is not running, has no pending republish, has no autopilot run other than
`published`, `rejected` or `expired`, and was rejected or published. Threads with no carousel project are never listed.

## Step 1 — Dry run (deletes nothing)

```bash
ssh "$DO_USER@$DO_HOST"
cd /opt/alter-ego
docker compose -f docker-compose.prod.yml exec -T backend \
  python -m rag_backend.scripts.checkpoint_prune --write-threads /tmp/threads.txt
docker compose -f docker-compose.prod.yml cp backend:/tmp/threads.txt ./threads.txt
```

One line per thread: project status, phase status, workflow status, public, archived, last update, and the
checkpoints / writes / blobs it would lose.

## Step 2 — Sign-off

Pedro reviews the list. Remove every thread he does not approve from `threads.txt`, then copy it back:

```bash
docker compose -f docker-compose.prod.yml cp ./threads.txt backend:/tmp/threads.txt
```

## Step 3 — Database backup

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -t checkpoints -t checkpoint_writes -t checkpoint_blobs "$POSTGRES_DB" \
  > "/opt/alter-ego/backups/checkpoints-$(date +%Y%m%d-%H%M%S).sql"
```

## Step 4 — Apply

```bash
docker compose -f docker-compose.prod.yml exec -T backend \
  python -m rag_backend.scripts.checkpoint_prune --apply \
  --threads /tmp/threads.txt --backup /tmp/checkpoint-prune-backup.jsonl
docker compose -f docker-compose.prod.yml cp \
  backend:/tmp/checkpoint-prune-backup.jsonl ./backups/
```

The run re-checks every signed-off thread under a row lock and refuses (exit 1, nothing deleted) if one is no
longer eligible. It writes every row it deletes to the backup file (which must not exist yet) and checks the count
before deleting, all in one transaction. A run that deletes nothing, or fewer rows than expected, exits 1 and rolls
back. Exit 2 is a usage error.

## Step 5 — Reclaim the space

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "VACUUM (ANALYZE) checkpoints, checkpoint_writes, checkpoint_blobs;"
```

`VACUUM FULL` returns the space to the disk but locks the tables; run it only outside carousel activity.
