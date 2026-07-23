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
# Dirty-tree guard (AE-0322): diff-based gates (lint-diff, strict-diff,
# integrity) compare COMMITTED HEAD vs origin/main, so uncommitted/untracked
# source files are INVISIBLE to them — a green run over a dirty tree can be a
# false green (the AE-0301 incident). The wrapper therefore refuses to run when
# in-scope source files are dirty. GATE_CAPTURE_ALLOW_DIRTY=1 downgrades the
# refusal to a loud warning and stamps `"dirty":N` into the echoed GATES_JSON
# line; the move-time guard (gate_proof.py) blocks a transition carrying
# dirty>0 unless the dev-summary has a DIRTY_WAIVER: line naming the files.
#
# Usage:   gate-capture.sh <backend|frontend|all|scope:gate>
# Env:     GATE_CAPTURE_LOG=path   override the capture log destination.
#          GATE_CAPTURE_ALLOW_DIRTY=1  run despite in-scope dirty source files
#                                      (stamps "dirty":N into GATES_JSON).
#          (Anything gates.sh honours — DATABASE_URL, GATES_REQUIRE_ALL — flows
#           through unchanged.)
# Exit:    the GATE's real exit code (0 PASS, 1+ FAIL count, 2 usage error /
#          dirty-tree refusal).
# =============================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$REPO_ROOT/scripts/ci"

SCOPE="${1:-}"
if [[ -z "$SCOPE" ]]; then
  echo "Usage: gate-capture.sh <backend|frontend|all|scope:gate>" >&2
  exit 2
fi

# --- Dirty-tree pre-flight (AE-0322) -----------------------------------------
# Source files git can't diff (untracked or modified) under the scope's dirs.
SOURCE_EXT_RE='\.(py|ts|tsx|js|jsx|mjs|cjs|sh)$'
scope_root="${SCOPE%%:*}"
case "$scope_root" in
  backend)  DIRTY_SCOPE_DIRS=(backend scripts) ;;
  frontend) DIRTY_SCOPE_DIRS=(frontend/src scripts) ;;
  *)        DIRTY_SCOPE_DIRS=(backend frontend/src scripts) ;;  # all / unknown: superset
esac

# --untracked-files=all: a fresh directory must list its files, not `dir/`.
dirty_files="$(git -C "$REPO_ROOT" status --porcelain --untracked-files=all -- "${DIRTY_SCOPE_DIRS[@]}" 2>/dev/null \
  | awk '{print $NF}' | grep -E "$SOURCE_EXT_RE" || true)"
dirty_count=0
if [[ -n "$dirty_files" ]]; then
  dirty_count="$(printf '%s\n' "$dirty_files" | wc -l | tr -d ' ')"
fi

if [[ "$dirty_count" -gt 0 ]]; then
  if [[ "${GATE_CAPTURE_ALLOW_DIRTY:-0}" != "1" ]]; then
    {
      echo "gate-capture: DIRTY TREE — $dirty_count uncommitted/untracked in-scope source file(s):"
      printf '%s\n' "$dirty_files" | sed 's/^/  /'
      echo "gate-capture: diff-based gates CANNOT see uncommitted work (AE-0322) — commit first,"
      echo "gate-capture: or set GATE_CAPTURE_ALLOW_DIRTY=1 to run anyway (stamps \"dirty\":N into GATES_JSON)."
    } >&2
    exit 2
  fi
  {
    echo "gate-capture: WARNING running over a dirty tree ($dirty_count in-scope source file(s)) —"
    echo "gate-capture: GATES_JSON will carry \"dirty\":$dirty_count; the Dev Complete/Review move"
    echo "gate-capture: will BLOCK without a DIRTY_WAIVER: line in the dev-summary (AE-0322)."
  } >&2
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
# Stamp the dirty count into the verdict line (AE-0322) so the pasted proof
# carries the taint and gate_proof.py can block an unwaived transition.
if [[ -n "$gates_line" && "$dirty_count" -gt 0 ]]; then
  gates_line="${gates_line/\{/{\"dirty\":$dirty_count,}"
fi
echo "-----------------------------------------------"
echo "gate-capture: log written to ${LOG#"$REPO_ROOT"/}"
if [[ -n "$gates_line" ]]; then
  echo "$gates_line"
else
  echo "gate-capture: WARNING no GATES_JSON line found (gates.sh may have errored early)." >&2
fi
echo "gate-capture: gate exit = ${gate_exit}"

exit "$gate_exit"
