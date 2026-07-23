#!/usr/bin/env bash
# =============================================================================
# regen_contracts.sh — regenerate ALL FOUR pinned API-contract artifacts in one
# fail-fast command, then verify them READ-ONLY before reporting success
# (AE-0325; kaizen session-2026-07-22 FC-5).
#
# The four artifacts every API-contract change must regenerate (each previously
# rediscovered via its own red gate):
#   1. docs/architecture/openapi.json          (scripts/export_openapi.py)
#   2. tests/snapshots/openapi_routes.json     (REGEN_ROUTE_SNAPSHOT=1 pytest)
#   3. tests/snapshots/publishing/*.json       (pytest --snapshot-update)
#   4. tests/snapshots/editorial/*.json        (pytest --snapshot-update)
#
# Fail-fast (WARN-5, cold-critic): the FIRST failing step aborts with an
# INCOMPLETE banner — a partial regen must never look done. The final phase
# re-runs all four checks read-only (no regen flags); only then exit 0.
#
# CWD landmine this kills: backend/scripts/export_openapi.py loads .env from
# the CURRENT directory — run from repo root it reads the root .env (whose
# ENCRYPTION_KEY the backend Settings reject). This script cd's into backend/
# itself, so it works from any caller directory.
#
# Usage:  bash scripts/dev/regen_contracts.sh   (or: make regen-contracts)
# Exit:   0 only when all four artifacts regenerated AND verified read-only.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT/backend"

CURRENT_STEP="startup"
on_error() {
  echo "" >&2
  echo "regen-contracts: ✗ regen INCOMPLETE — artifacts may be INCONSISTENT (failed at: $CURRENT_STEP)." >&2
  echo "regen-contracts: fix the failure and re-run the WHOLE script; do not commit a partial regen." >&2
}
trap on_error ERR

step() {
  CURRENT_STEP="$1"
  echo ""
  echo "regen-contracts: [$CURRENT_STEP]"
}

step "regen 1/4 openapi.json"
uv run python scripts/export_openapi.py

step "regen 2/4 route snapshot"
REGEN_ROUTE_SNAPSHOT=1 uv run pytest tests/unit/test_route_snapshot.py -q

step "regen 3/4 publishing snapshots"
uv run pytest tests/integration/test_publishing_safety_net.py --snapshot-update -q

step "regen 4/4 editorial workflow snapshots"
uv run pytest tests/integration/test_carousel_workflow_safety_net.py --snapshot-update -q

# --- Read-only verification (no regen flags): a half-updated state cannot pass.
step "verify 1/2 openapi.json --check"
uv run python scripts/export_openapi.py --check

step "verify 2/2 snapshot tests (read-only)"
uv run pytest tests/unit/test_route_snapshot.py \
  tests/integration/test_publishing_safety_net.py \
  tests/integration/test_carousel_workflow_safety_net.py -q

echo ""
echo "regen-contracts: ✓ all four contract artifacts regenerated and verified read-only."
echo "regen-contracts: review the diff (git status) and commit the artifacts with your change."
