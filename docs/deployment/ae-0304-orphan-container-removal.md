# AE-0304 — orphan test-container removal record (2026-07-02)

## What was removed

Two unmanaged containers, running since 2026-06-12 with `restart=unless-stopped`
(leftovers of the 2026-06-12 Langfuse S3-upload debugging session):

- `minio-test` (`minio/minio`, named volume `minio_test_data`, port 9000
  unpublished, network `alter-ego_default`)
- `langfuse-worker-test` (`langfuse/langfuse-worker:3` floating tag, no mounts)

**Why it mattered beyond hygiene:** `langfuse-worker-test` was **live on the
real infrastructure** — real Postgres (`postgres:5432/langfuse`), real Redis,
real ClickHouse — while pointing `LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT` at
`http://minio-test:9000`. A second, version-floating worker consuming the real
queue and uploading blobs to the wrong MinIO. Its removal is a data-integrity
fix, not just cleanup.

## Orphan verification (AC evidence)

- Compose: not in `docker-compose.prod.yml`; the creator was the ad-hoc
  `/opt/alter-ego/compose.langfuse-s3-test.yml` (env-override fragment) —
  itself relocated, see below.
- `/root/.bash_history`: 0 references. Root crontab: none. `/etc/cron.*`,
  `/etc/systemd/system`: none.
- Enumerated systemd timer set (the soak measurement list, all OS-level, none
  docker-touching): sysstat-collect, droplet-agent-update, fwupd-refresh,
  apt-daily-upgrade, apt-daily, motd-news, man-db, certbot,
  update-notifier-download, systemd-tmpfiles-clean, dpkg-db-backup, logrotate,
  sysstat-summary (daily); e2scrub_all, fstrim (weekly).

## Reversibility artifacts (on the droplet, `/root/env-backups/ae-0304/`, 700/600)

- `minio-test.inspect.json`, `langfuse-worker-test.inspect.json` — full config
  (image, env, mounts, network, command) for recreation.
- `minio_test_data.tar.gz` — the non-empty volume (380K: six Jun-12 debug
  trace objects), sha256
  `6d3acfbfddfbf2571e141db897b20896c8b8c2242f46aa44ebee3afea4077a21`.
- `compose.langfuse-s3-test.yml` — relocated out of `/opt/alter-ego` because it
  contains the **real `LANGFUSE_MINIO_PASSWORD` in plaintext** (see Security
  note).

## Off-box restore demo (AC: proven, not assumed)

On a dev host: snapshot copied (sha256 verified) → extracted → mounted into a
fresh `minio/minio` with the original `MINIO_ROOT_USER/PASSWORD` from the
inspect artifact → `mc ls -r` listed all 6 objects → `mc cat` read
`test-evt-minio.json` back intact. (Root creds live in container env, not the
volume — the inspect artifact is required for rehydration; recorded here so the
next restore doesn't rediscover it.)

## Removal + result

```
docker rm -f minio-test langfuse-worker-test
docker volume rm minio_test_data          # after snapshot + restore proof
docker image prune -f                     # reclaimed ~1G (langfuse-worker:3)
```

- Disk: 91G/79% → 90G/78%.
- `docker ps -a` now shows **only** compose-managed containers.
- Reboot-survival: nothing can recreate them — the `unless-stopped` policy died
  with the containers and no compose/cron/systemd references remain.
- `minio/minio:latest` tag intentionally kept: it points at the same digest the
  compose-managed MinIO pins (`minio/minio@sha256:14cea…`); deleting the tag
  frees nothing and forcing it is wrong.
- Post-cleanup smoke: site 200, backend `/health` 200, Langfuse health 200,
  the real `langfuse-worker-1` executing jobs. (Carousel smoke: open — runs
  with the next authenticated prod carousel; the removed containers are not on
  that path.)

## Soak gate for AE-0303 (hard `Blocks`)

Soak started **2026-07-02 ~04:00 UTC** (removal time). AE-0303's reboot may
proceed only after **≥24h AND every timer in the enumerated daily list above
has fired once** against the post-removal state — verify with
`systemctl list-timers --all` (LAST column past 2026-07-02 04:00 UTC), don't
treat 24h as a pure wall-clock proxy.

## Security note (follow-up)

`compose.langfuse-s3-test.yml` carried the **real** `LANGFUSE_MINIO_PASSWORD`
in plaintext in the deploy dir (644-era exposure, same window as AE-0301).
`LANGFUSE_MINIO_PASSWORD` is therefore added to the cheap-rotation list in
[ae-0301-key-rotation-runbook.md](ae-0301-key-rotation-runbook.md).

## Hygiene rule

**Production runs only compose-managed containers.** Ad-hoc debug/test
containers (and any ad-hoc compose override files) must be removed in the same
session that creates them; anything needing to persist gets a ticket and a
place in `docker-compose.prod.yml`. See also DEPLOYMENT_GUIDE §9.
