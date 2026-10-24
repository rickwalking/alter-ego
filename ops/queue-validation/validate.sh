#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "${1:-}" = "--target" ] && [ "${2:-}" = "prod" ]; then
  exec python3 "$HERE/prod_validate.py"
fi
REPO="$(cd "$HERE/../.." && pwd)"
REGION="${DO_REGION:-nyc1}"
SIZE="${DO_SIZE:-s-2vcpu-4gb}"
IMAGE="${DO_IMAGE:-docker-20-04}"
THEMES="${VALIDATION_THEMES:-3}"
LOAD_SECONDS="${VALIDATION_LOAD_SECONDS:-240}"
RUN_TIMEOUT_SECONDS="${VALIDATION_RUN_TIMEOUT_SECONDS:-3600}"
NAME="queue-validation-$(date +%Y%m%d%H%M%S)"
API=https://api.digitalocean.com/v2
OUT="${VALIDATION_OUT:-$HOME/queue-validation-results/$NAME}"

: "${DO_TOKEN_FILE:?set DO_TOKEN_FILE to a file outside the repo holding the DigitalOcean token}"
: "${PROD_HASHES_FILE:?set PROD_HASHES_FILE to the production value hashes (see README)}"
case "$(realpath "$DO_TOKEN_FILE")" in "$REPO"/*) echo "the token file must live outside the repo" >&2; exit 2;; esac

WORK="$(mktemp -d)"
SCOUT_KEY="$(openssl rand -hex 24)"
mkdir -p "$OUT"
KEY="$WORK/id_ed25519"
DROPLET_ID=""
FIREWALL_ID=""
KEY_ID=""
IP=""

api() {
  local method="$1" path="$2" body="${3:-}"
  local args=(-fsS -X "$method" -H "Content-Type: application/json" -H @"$WORK/auth")
  [ -n "$body" ] && args+=(-d "$body")
  curl "${args[@]}" "$API$path"
}

teardown() {
  set +e
  [ -n "$DROPLET_ID" ] && api DELETE "/droplets/$DROPLET_ID" >/dev/null && echo "droplet $DROPLET_ID deleted"
  [ -n "$FIREWALL_ID" ] && sleep 5 && api DELETE "/firewalls/$FIREWALL_ID" >/dev/null && echo "firewall deleted"
  [ -n "$KEY_ID" ] && api DELETE "/account/keys/$KEY_ID" >/dev/null && echo "ssh key deleted"
  rm -rf "$WORK"
}
trap teardown EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

ssh_droplet() {
  ssh -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR "root@$IP" "$@"
}

remote() {
  ssh_droplet "SCOUT_KEY='$SCOUT_KEY' bash /opt/alter-ego/ops/queue-validation/remote.sh $*"
}

firewall_rules() {
  local outbound="$1"
  jq -n --arg me "$MY_IP/32" --argjson id "$DROPLET_ID" --arg name "$NAME" --argjson out "$outbound" '{
    name: $name, droplet_ids: [$id],
    inbound_rules: [
      {protocol: "tcp", ports: "22", sources: {addresses: [$me]}},
      {protocol: "tcp", ports: "80", sources: {addresses: [$me]}}
    ],
    outbound_rules: $out
  }'
}

provision() {
  printf 'Authorization: Bearer %s\n' "$(tr -d '[:space:]' < "$DO_TOKEN_FILE")" > "$WORK/auth"
  chmod 600 "$WORK/auth"
  ssh-keygen -q -t ed25519 -N "" -f "$KEY"
  KEY_ID="$(api POST /account/keys "$(jq -n --arg n "$NAME" --arg k "$(cat "$KEY.pub")" '{name: $n, public_key: $k}')" | jq -r .ssh_key.id)"
  DROPLET_ID="$(api POST /droplets "$(jq -n --arg n "$NAME" --arg r "$REGION" --arg s "$SIZE" --arg i "$IMAGE" --argjson k "$KEY_ID" \
    '{name: $n, region: $r, size: $s, image: $i, ssh_keys: [$k], tags: ["queue-validation"], monitoring: false}')" | jq -r .droplet.id)"
  for _ in $(seq 1 60); do
    IP="$(api GET "/droplets/$DROPLET_ID" | jq -r '.droplet.networks.v4[] | select(.type == "public") | .ip_address' | head -1)"
    [ -n "$IP" ] && break
    sleep 5
  done
  MY_IP="$(curl -fsS https://api.ipify.org)"
  local open_egress='[{"protocol":"tcp","ports":"all","destinations":{"addresses":["0.0.0.0/0","::/0"]}},{"protocol":"udp","ports":"all","destinations":{"addresses":["0.0.0.0/0","::/0"]}}]'
  FIREWALL_ID="$(api POST /firewalls "$(firewall_rules "$open_egress")" | jq -r .firewall.id)"
  for _ in $(seq 1 60); do ssh_droplet true 2>/dev/null && break; sleep 5; done
  echo "droplet $DROPLET_ID ($SIZE, $REGION) at $IP"
}

ship_branch() {
  git -C "$REPO" archive --format=tar HEAD | ssh_droplet "mkdir -p /opt/alter-ego && tar -x -C /opt/alter-ego"
  git -C "$REPO" rev-parse HEAD > "$OUT/commit.txt"
}

lock_egress() {
  local closed='[{"protocol":"icmp","destinations":{"addresses":["'"$MY_IP"'/32"]}}]'
  api PUT "/firewalls/$FIREWALL_ID" "$(firewall_rules "$closed")" >/dev/null
  if ssh_droplet "curl -m 10 -fsS -o /dev/null https://api.telegram.org" 2>/dev/null; then
    echo "egress is still open" >&2
    exit 1
  fi
  echo "egress closed"
}

write_env() {
  SCOUT_KEY="$SCOUT_KEY" bash "$HERE/env_template.sh" > "$WORK/env"
  python3 "$HERE/credential_check.py" "$WORK/env" "$PROD_HASHES_FILE" | tee "$OUT/credential-check.txt"
  scp -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR "$WORK/env" "root@$IP:/opt/alter-ego/.env"
  scp -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR "$PROD_HASHES_FILE" "root@$IP:/root/prod-hashes.txt"
  ssh_droplet "chmod 600 /opt/alter-ego/.env && python3 /opt/alter-ego/ops/queue-validation/credential_check.py /opt/alter-ego/.env /root/prod-hashes.txt && rm /root/prod-hashes.txt"
}

load() {
  python3 "$HERE/load_p95.py" "http://$IP" "$1" 2 --samples "$OUT/$2.samples" | tee "$OUT/$2.json"
}

wait_for() {
  local check="$1" op="$2" want="$3" limit="$4"
  for _ in $(seq 1 "$((limit / 10))"); do
    [ "$(remote "$check" | tr -d '[:space:]')" "$op" "$want" ] && return 0
    sleep 10
  done
  return 1
}

load_while_active() {
  local window=0
  while [ "$(remote active | tr -d '[:space:]')" -gt 0 ]; do
    window=$((window + 1))
    python3 "$HERE/load_p95.py" "http://$IP" 120 2 --samples "$OUT/under-generation.samples" > "$OUT/under-generation-$window.json"
  done
}

revert_rehearsal() {
  local base
  base="$(git -C "$REPO" merge-base origin/main HEAD)"
  echo "$base" > "$OUT/revert-base.txt"
  git -C "$REPO" archive --format=tar "$base" | ssh_droplet "mkdir -p /opt/alter-ego-revert && tar -x -C /opt/alter-ego-revert"
  ssh_droplet "SEED_OFFSET=5 bash /opt/alter-ego/ops/queue-validation/remote.sh seed 2" | tee "$OUT/revert-seeded-runs.json"
  wait_for running -ge 1 900 || true
  sleep 60
  remote revert_rehearsal > "$OUT/revert-rehearsal.txt" 2>&1
  ssh_droplet "docker compose -p alter-ego -f /opt/alter-ego-revert/docker-compose.prod.yml -f /opt/alter-ego-revert/compose.revert.yml exec -T postgres psql -U rag_user -d rag_db -tAc \"SELECT count(*) FROM autopilot_runs WHERE state IN ('queued','generating','reworking')\"" > "$OUT/revert-active-before.txt"
  for _ in $(seq 1 "$((RUN_TIMEOUT_SECONDS / 30))"); do
    local left
    left="$(ssh_droplet "docker compose -p alter-ego -f /opt/alter-ego-revert/docker-compose.prod.yml -f /opt/alter-ego-revert/compose.revert.yml exec -T postgres psql -U rag_user -d rag_db -tAc \"SELECT count(*) FROM autopilot_runs WHERE state IN ('queued','generating','reworking')\"" | tr -d '[:space:]')"
    [ "$left" = "0" ] && { echo "revert: no run stranded" | tee "$OUT/revert-verdict.txt"; return 0; }
    sleep 30
  done
  echo "revert: runs still active at the timeout" | tee "$OUT/revert-verdict.txt"
}

main() {
  provision
  ship_branch
  remote prepare
  lock_egress
  write_env
  remote up
  remote sample_start
  load "$LOAD_SECONDS" idle-baseline
  remote seed "$THEMES" | tee "$OUT/seeded-runs.json"
  load_while_active &
  local load_pid=$!
  wait_for running -ge 1 900 || true
  sleep 60
  remote kill_worker | tee "$OUT/chaos-kill.txt"
  wait_for running -ge 1 900 || true
  sleep 90
  remote deploy_cycle > "$OUT/chaos-deploy.txt" 2>&1
  wait_for active -eq 0 "$RUN_TIMEOUT_SECONDS" || echo "runs still active at the timeout" | tee "$OUT/timeout.txt"
  wait "$load_pid" || true
  python3 "$HERE/load_p95.py" --summarize "$OUT/idle-baseline.samples" "$OUT/under-generation.samples" | tee "$OUT/p95-verdict.json"
  revert_rehearsal
  load "$LOAD_SECONDS" after-runs
  remote report | tee "$OUT/report.tsv"
  ssh_droplet "cat /root/validation-samples.tsv" > "$OUT/memory-samples.tsv"
  echo "results in $OUT"
}

main "$@"
