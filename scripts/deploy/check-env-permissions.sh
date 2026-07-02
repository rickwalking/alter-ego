#!/usr/bin/env bash
# AE-0301: production secret files must never be world-readable.
#
# Usage: check-env-permissions.sh <deploy-dir> <env-file>...
#
# Exits non-zero (failing the deploy that invokes it) when:
#   - any given env file is missing, not mode 600, or not owned by the
#     expected owner (defaults to the invoking user — root on the droplet), or
#   - any plaintext .env.backup* copy exists in <deploy-dir> (the 2026-06-02
#     manual backup incident must not recur).
#
# Invoked at the end of the prod deploy (.github/workflows/deploy.yml) as a
# stat-based assertion, not a log line: a permissions regression FAILS the
# deploy. Override the owner expectation in tests via ENV_PERMS_EXPECTED_OWNER.
#
# Rule-fires regression test (AE-0180 standard):
#   backend/tests/unit/scripts_ci/test_check_env_permissions.py

set -euo pipefail

REQUIRED_MODE="600"
EXPECTED_OWNER="${ENV_PERMS_EXPECTED_OWNER:-$(id -un)}"
FAIL_PREFIX="ENV-PERMS FAIL:"

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <deploy-dir> <env-file>..." >&2
  exit 2
fi

deploy_dir="$1"
shift

fail=0
for env_file in "$@"; do
  if [ ! -e "$env_file" ]; then
    echo "${FAIL_PREFIX} missing expected secret file: ${env_file}" >&2
    fail=1
    continue
  fi
  mode="$(stat -c '%a' "$env_file")"
  owner="$(stat -c '%U' "$env_file")"
  if [ "$mode" != "$REQUIRED_MODE" ] || [ "$owner" != "$EXPECTED_OWNER" ]; then
    echo "${FAIL_PREFIX} ${env_file} is ${mode} ${owner} (want ${REQUIRED_MODE} ${EXPECTED_OWNER})" >&2
    fail=1
  fi
done

# Unmatched glob stays literal, so -e is false when no backup exists.
backups=("${deploy_dir}"/.env.backup*)
if [ -e "${backups[0]}" ]; then
  echo "${FAIL_PREFIX} plaintext secret backup present: ${backups[*]}" >&2
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  exit 1
fi

echo "ENV-PERMS OK: $* are ${REQUIRED_MODE} ${EXPECTED_OWNER}; no .env.backup* in ${deploy_dir}"
