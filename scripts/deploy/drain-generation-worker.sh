#!/usr/bin/env bash
# Drain the generation worker before the deploy stops it (AE-0598).
#
# Pedro's decision (2026-11-02): the deploy pauses new job pickup and lets the job
# in flight reach its next phase boundary, so a deploy does not kill an autopilot
# run. The worker side is rag_backend.worker.drain / drain_cli.
#
#   drain-generation-worker.sh drain <compose-file> <max-wait-seconds> <poll-seconds>
#     Sets the drain flag in the running worker, then polls `drain_cli idle` until
#     no generation job is in flight or <max-wait-seconds> (wall clock) have passed.
#   drain-generation-worker.sh clear <compose-file>
#     Removes the drain flag in the (new) worker. The worker also removes it when it
#     starts and ignores a flag older than its time-to-live, so this is a backstop.
#
# Both modes exit 0 whatever the worker answers: the drain never blocks a deploy.
# When the wait runs out the deploy stops the worker as before; the killed drive
# stays `running` with its PgQueuer job picked, PgQueuer re-picks it once its
# heartbeat is older than --heartbeat-timeout and the drive re-runs the phase from
# the last checkpoint. Exit 2 only on a usage error (the stack is untouched then).
set -u

readonly SERVICE="generation-worker"
readonly CLI_MODULE="rag_backend.worker.drain_cli"
readonly EXIT_USAGE=2
readonly USAGE="usage: $0 drain <compose-file> <max-wait-seconds> <poll-seconds> | clear <compose-file>"

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

worker_cli() {
  compose exec -T "$SERVICE" python -m "$CLI_MODULE" "$1" >/dev/null 2>&1
}

worker_running() {
  [ -n "$(compose ps -q --status running "$SERVICE" 2>/dev/null)" ]
}

usage() {
  echo "$USAGE" >&2
  exit "$EXIT_USAGE"
}

is_count() {
  case "$1" in
    '' | *[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

drain() {
  local max_wait="$1" poll="$2" started
  if ! worker_running; then
    echo "DRAIN: ${SERVICE} is not running, nothing to drain"
    return 0
  fi
  if ! worker_cli drain; then
    echo "::warning::DRAIN: could not set the drain flag in ${SERVICE}; stopping it without a drain"
    return 0
  fi
  echo "DRAIN: flag set, waiting up to ${max_wait}s for the job in flight"
  started=$SECONDS
  while true; do
    if worker_cli idle; then
      echo "DRAIN: ${SERVICE} idle after $((SECONDS - started))s"
      return 0
    fi
    if [ $((SECONDS - started)) -gt "$max_wait" ]; then
      echo "::warning::DRAIN: ${SERVICE} still busy after ${max_wait}s; stopping it anyway, the run resumes from its last checkpoint on the next worker"
      return 0
    fi
    sleep "$poll"
  done
}

clear_flag() {
  if ! worker_running; then
    echo "::warning::DRAIN: ${SERVICE} is not running after the deploy; no drain flag to clear"
    return 0
  fi
  if ! worker_cli clear; then
    echo "::warning::DRAIN: could not clear the drain flag in ${SERVICE}; it expires on its own"
    return 0
  fi
  echo "DRAIN: flag cleared"
}

MODE="${1:-}"
COMPOSE_FILE="${2:-}"
[ -n "$COMPOSE_FILE" ] || usage

case "$MODE" in
  drain)
    [ "$#" -eq 4 ] || usage
    is_count "$3" || usage
    is_count "$4" || usage
    drain "$3" "$4"
    ;;
  clear)
    [ "$#" -eq 2 ] || usage
    clear_flag
    ;;
  *)
    usage
    ;;
esac
