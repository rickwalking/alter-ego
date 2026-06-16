#!/usr/bin/env bash
# =============================================================================
# external_agent.sh — shared mechanics for running a prompt through an external
# LLM CLI (OpenCode / Codex / Cursor). Sourced by:
#   - scripts/qa/run_external_qa.sh        (bias-free QA review)
#   - scripts/kaizen/run_external_kaizen.sh (cost-offloaded improvement analysis)
#
# Encapsulates the operational hardening learned in Wave-1 QA so it lives in ONE
# place (no drift between two copies of the fragile OpenCode hang-recovery):
#   - tool fallback (requested -> opencode -> codex -> cursor-agent)
#   - clean-kill before OpenCode launches (stale instances hang at init)
#   - stream health check ("stream providerID" within N seconds) + one retry
#   - ANSI stripping
#
# This file defines functions only; it runs nothing at source time and does NOT
# set shell options — the wrapper owns `set -euo pipefail`.
#
# Env knobs (optional):
#   EXTERNAL_STREAM_WAIT_SECS   default 90   (OpenCode must stream within this)
#   EXTERNAL_RUN_TIMEOUT_SECS   default 1500 (hard per-run timeout)
#     (QA_RUN_TIMEOUT_SECS is honored as a back-compat fallback)
# =============================================================================

EXT_OPENCODE_LOG="${EXT_OPENCODE_LOG:-$HOME/.local/share/opencode/log/opencode.log}"
EXT_STREAM_WAIT_SECS="${EXTERNAL_STREAM_WAIT_SECS:-90}"
EXT_RUN_TIMEOUT_SECS="${EXTERNAL_RUN_TIMEOUT_SECS:-${QA_RUN_TIMEOUT_SECS:-1500}}"

# Resolve repo root from this lib's location (scripts/lib/ -> repo root).
EXT_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ext_pick_tool <requested> -> prints the first installed CLI, or "none".
ext_pick_tool() {
  local requested="${1:-opencode}" candidate
  for candidate in "$requested" opencode codex cursor-agent; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"; return
    fi
  done
  echo "none"
}

ext_strip_ansi() { sed -e 's/\x1b\[[0-9;]*m//g' "$1" > "$1.clean" && mv "$1.clean" "$1"; }

# _ext_run_opencode <prompt-file> <output-file> -> 0 if it streamed, 3 if hung.
_ext_run_opencode() {
  local prompt_file="$1" output_file="$2"
  pkill -9 opencode 2>/dev/null || true
  local marker
  marker=$(wc -l < "$EXT_OPENCODE_LOG" 2>/dev/null || echo 0)
  timeout "$EXT_RUN_TIMEOUT_SECS" opencode run --agent plan "$(cat "$prompt_file")" \
    > "$output_file" 2> "$output_file.log" &
  local pid=$! waited=0
  while [ "$waited" -lt "$EXT_STREAM_WAIT_SECS" ]; do
    if tail -n +"$((marker + 1))" "$EXT_OPENCODE_LOG" 2>/dev/null | grep -q "stream providerID"; then
      wait "$pid" || true; return 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" || true; return 0   # finished fast (small prompt) — let caller decide
    fi
    sleep 5; waited=$((waited + 5))
  done
  echo "WARN: opencode never reached streaming after ${EXT_STREAM_WAIT_SECS}s — killing (hung-at-init)" >&2
  kill -9 "$pid" 2>/dev/null || true
  pkill -9 opencode 2>/dev/null || true
  return 3
}

_ext_run_codex() {
  timeout "$EXT_RUN_TIMEOUT_SECS" codex exec --sandbox read-only --skip-git-repo-check \
    -C "$EXT_REPO_ROOT" - < "$1" > "$2" 2> "$2.log" || true
}

_ext_run_cursor() {
  timeout "$EXT_RUN_TIMEOUT_SECS" cursor-agent --print "$(cat "$1")" \
    > "$2" 2> "$2.log" || true
}

# ext_run <tool> <prompt-file> <output-file>
#   Runs the prompt; for OpenCode retries once on a hung launch.
#   Returns 0 on a run that produced output, 3 on launch failure / double-hang.
ext_run() {
  local tool="$1" prompt_file="$2" output_file="$3"
  echo "external-agent: tool=$tool prompt=$prompt_file" >&2
  case "$tool" in
    opencode)
      if ! _ext_run_opencode "$prompt_file" "$output_file"; then
        echo "external-agent: retrying once after hung launch" >&2
        _ext_run_opencode "$prompt_file" "$output_file" || {
          echo "ERROR: opencode hung twice" >&2; return 3; }
      fi
      ;;
    codex)               _ext_run_codex "$prompt_file" "$output_file" ;;
    cursor-agent|cursor) _ext_run_cursor "$prompt_file" "$output_file" ;;
    none|*) echo "ERROR: no external CLI available (opencode/codex/cursor-agent)" >&2; return 3 ;;
  esac
  return 0
}
