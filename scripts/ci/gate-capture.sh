#!/usr/bin/env bash
# =============================================================================
# gate-capture.sh — run the FULL gate set and capture its real exit + GATES_JSON
# to a deterministic file, so the verdict cannot be masked by a trailing pipe.
#
# The failure this fixes (AE-0259): `gates.sh <scope> | tail -n45` returns the
# PIPE's exit (tail = 0), hiding a non-zero gate — a red PR was misread as green.
# This wrapper does NOT pipe: it redirects gates.sh stdout+stderr to a log file
# and propagates gates.sh's OWN exit code. It bridges AE-0258 by echoing the
# machine-readable GATES_JSON line for pasting into the dev-summary / qa report.
#
# It always runs the FULL gate set for <scope> (never --changed-only): the
# Dev Complete declaration must be based on a full run (AE-0259). Use
# `gates.sh <scope> --changed-only` directly for fast iteration.
#
# Usage:   gate-capture.sh <backend|frontend|all|scope:gate>
# Env:     GATE_CAPTURE_LOG=path   override the capture log destination.
#          (Anything gates.sh honours — DATABASE_URL, GATES_REQUIRE_ALL — flows
#           through unchanged.)
# Exit:    the GATE's real exit code (0 PASS, 1+ FAIL count, 2 usage error).
# =============================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$REPO_ROOT/scripts/ci"

SCOPE="${1:-}"
if [[ -z "$SCOPE" ]]; then
  echo "Usage: gate-capture.sh <backend|frontend|all|scope:gate>" >&2
  exit 2
fi

REPORTS_DIR="$REPO_ROOT/.agent/reports"
mkdir -p "$REPORTS_DIR"
# Deterministic per-scope log path (':' in scope:gate → '-' for a valid filename).
DEFAULT_LOG="$REPORTS_DIR/.gates-capture-${SCOPE//:/-}.log"
LOG="${GATE_CAPTURE_LOG:-$DEFAULT_LOG}"

# Run the FULL gate set, redirecting BOTH streams to the log file. No pipe is
# involved, so $? below is gates.sh's own exit — not a pipe component's.
bash "$SCRIPT_DIR/gates.sh" "$SCOPE" >"$LOG" 2>&1
gate_exit=$?

# Surface the captured log and the machine-readable verdict line (AE-0258).
cat "$LOG"
gates_line="$(grep -F 'GATES_JSON:' "$LOG" | tail -n1 || true)"
echo "-----------------------------------------------"
echo "gate-capture: log written to ${LOG#"$REPO_ROOT"/}"
if [[ -n "$gates_line" ]]; then
  echo "$gates_line"
else
  echo "gate-capture: WARNING no GATES_JSON line found (gates.sh may have errored early)." >&2
fi
echo "gate-capture: gate exit = ${gate_exit}"

exit "$gate_exit"
