#!/bin/sh
# AE-0302: production Redis entrypoint — fail closed, auth required, admin
# commands disabled.
#
# Symmetric with the backend's fail-closed gate: an empty/absent
# REDIS_PASSWORD in a production-like environment must make the container
# REFUSE TO START. Naively passing `--requirepass "$REDIS_PASSWORD"` with an
# empty var starts an OPEN (unauthenticated) Redis while the backend fails
# closed — the exact hole this ticket closes, with the app down so nobody
# notices. Only an explicit dev/test/local ENVIRONMENT tolerates no password;
# unset or unrecognized values require one (fail-closed direction).
#
# rename-command lines disable the admin verbs a compromised-but-authed peer
# could use to silently re-open Redis (`CONFIG SET requirepass ""`) or destroy
# data. The build-time config-integrity assertion for these lines lives in
# backend/tests/unit/scripts_ci/test_redis_entrypoint.py; the runtime "auth is
# required" proof is the deploy's NOAUTH probe (the two checks are deliberately
# separate — with CONFIG disabled, `CONFIG GET requirepass` cannot self-verify).
# BullMQ compatibility: langfuse-worker runs BullMQ 5.x (ioredis), which
# tolerates an unavailable CONFIG (standard on ElastiCache/MemoryDB); verified
# against the deployed langfuse-worker:3.185 at rollout.
#
# Rule-fires regression test (AE-0180):
#   backend/tests/unit/scripts_ci/test_redis_entrypoint.py

set -eu

case "${ENVIRONMENT:-}" in
  development | dev | test | local)
    if [ -z "${REDIS_PASSWORD:-}" ]; then
      echo "redis-entrypoint: ${ENVIRONMENT:-} environment, starting WITHOUT auth (dev-only path)" >&2
      exec redis-server --appendonly yes
    fi
    ;;
  *)
    if [ -z "${REDIS_PASSWORD:-}" ]; then
      echo "redis-entrypoint: FATAL — REDIS_PASSWORD is empty/unset in a production-like environment (ENVIRONMENT='${ENVIRONMENT:-}'). Refusing to start an open Redis. Set the REDIS_PASSWORD secret." >&2
      exit 1
    fi
    ;;
esac

exec redis-server \
  --appendonly yes \
  --requirepass "$REDIS_PASSWORD" \
  --rename-command CONFIG "" \
  --rename-command FLUSHALL "" \
  --rename-command FLUSHDB "" \
  --rename-command DEBUG "" \
  --rename-command SHUTDOWN ""
