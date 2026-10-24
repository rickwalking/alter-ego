#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/alter-ego
COMPOSE=(docker compose -f docker-compose.prod.yml -f ops/queue-validation/compose.validation.yml)
SAMPLES=/root/validation-samples.tsv
cd "$APP_DIR"

psql_app() {
  "${COMPOSE[@]}" exec -T postgres psql -U rag_user -d rag_db "$@"
}

prepare() {
  if ! swapon --show | grep -q /swapfile; then
    fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  fi
  "${COMPOSE[@]}" pull --ignore-pull-failures --quiet llm-mock postgres redis nginx
  "${COMPOSE[@]}" build
}

one_shots() {
  "${COMPOSE[@]}" up -d postgres
  for _ in $(seq 1 30); do
    "${COMPOSE[@]}" exec -T postgres pg_isready -U rag_user >/dev/null 2>&1 && break
    sleep 2
  done
  "${COMPOSE[@]}" run --rm --no-deps backend python -m rag_backend.scripts.generation_queue_schema --apply --verify
}

up() {
  one_shots
  "${COMPOSE[@]}" up -d
  for _ in $(seq 1 60); do
    curl -fsS -o /dev/null http://127.0.0.1/api/health && return 0
    sleep 5
  done
  echo "stack did not become healthy" >&2
  return 1
}

sample_start() {
  nohup bash -c "while true; do docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' | sed \"s/^/\$(date +%s)\t/\" >> $SAMPLES; free -m | awk '/Mem:/{print \"'\$(date +%s)'\thost\t\"\$3\"\t\"\$7}' >> $SAMPLES; sleep 15; done" >/dev/null 2>&1 &
}

seed() {
  "${COMPOSE[@]}" cp ops/queue-validation/seed.py backend:/tmp/seed.py
  "${COMPOSE[@]}" exec -T -e SEED_OFFSET="${SEED_OFFSET:-0}" backend python /tmp/seed.py "${1:-3}"
}

running() {
  psql_app -tAc "SELECT count(*) FROM generation_runs WHERE status = 'running'"
}

active() {
  psql_app -tAc "SELECT count(*) FROM autopilot_runs WHERE state IN ('queued', 'generating', 'reworking')"
}

kill_worker() {
  docker kill --signal KILL "$("${COMPOSE[@]}" ps -q generation-worker)"
  sleep 20
  "${COMPOSE[@]}" up -d generation-worker
}

deploy_cycle() {
  "${COMPOSE[@]}" build
  "${COMPOSE[@]}" stop -t 300 generation-worker || true
  "${COMPOSE[@]}" down -t 120
  up
}

revert_rehearsal() {
  local revert_dir=/opt/alter-ego-revert
  "${COMPOSE[@]}" stop -t 300 generation-worker
  "${COMPOSE[@]}" run --rm --no-deps backend python -m rag_backend.scripts.generation_queue_rollback --apply
  cp .env "$revert_dir/.env"
  sed '/^  generation-worker:/,/^$/d' ops/queue-validation/compose.validation.yml > "$revert_dir/compose.revert.yml"
  cp ops/queue-validation/mock_upstream.py "$revert_dir/"
  cd "$revert_dir"
  local revert=(docker compose -p alter-ego -f docker-compose.prod.yml -f compose.revert.yml)
  sed -i 's#./ops/queue-validation:/mock:ro#./:/mock:ro#' compose.revert.yml
  "${revert[@]}" build
  "${revert[@]}" down --remove-orphans
  "${revert[@]}" up -d
  docker ps -aq --filter name=generation-worker | xargs -r docker rm -f
  cd "$APP_DIR"
}

report() {
  psql_app -f - < ops/queue-validation/report.sql
  echo "oom_killed"
  for container in $("${COMPOSE[@]}" ps -aq); do
    docker inspect --format '{{.Name}}\t{{.State.OOMKilled}}\t{{.RestartCount}}' "$container"
  done
  echo "kernel_oom_lines"
  dmesg | grep -ci "out of memory" || true
  echo "mock_calls"
  "${COMPOSE[@]}" exec -T llm-mock python -c "import collections,json;c=collections.Counter(json.loads(l)['path'] for l in open('/logs/mock.jsonl'));print(json.dumps(c))"
  echo "worker_resumes"
  "${COMPOSE[@]}" logs generation-worker | grep -c generation_run_orphan_reaped || true
}

"$@"
