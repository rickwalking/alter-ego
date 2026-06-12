#!/usr/bin/env bash
# External QA orchestrator (qa-agent skill).
#
# Runs a QA prompt through an external LLM CLI (OpenCode / Codex /
# Cursor) with the operational hardening learned in Wave 1 QA:
#   - clean-kill before OpenCode launches (stale instances hang at init)
#   - stream health check: a healthy OpenCode run reaches
#     "stream providerID" in seconds; hung runs never do
#   - one automatic retry on a hung launch
#   - ANSI stripping and QA_VERDICT extraction from the output
#
# Usage:
#   scripts/qa/run_external_qa.sh <prompt-file> <output-file> [tool]
#
# tool: opencode (default) | codex | cursor — falls back down that list
# if the requested tool is not installed.
#
# Exit codes: 0=PASS, 10=WARN, 20=FAIL, 2=no verdict produced, 3=launch
# failed after retry.
set -euo pipefail

PROMPT_FILE="${1:?usage: run_external_qa.sh <prompt-file> <output-file> [tool]}"
OUTPUT_FILE="${2:?usage: run_external_qa.sh <prompt-file> <output-file> [tool]}"
TOOL="${3:-opencode}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OPENCODE_LOG="$HOME/.local/share/opencode/log/opencode.log"
STREAM_WAIT_SECS=90
RUN_TIMEOUT_SECS="${QA_RUN_TIMEOUT_SECS:-1500}"

pick_tool() {
  for candidate in "$TOOL" opencode codex cursor-agent; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return
    fi
  done
  echo "none"
}

strip_ansi() { sed -e 's/\x1b\[[0-9;]*m//g' "$1" > "$1.clean" && mv "$1.clean" "$1"; }

extract_verdict() {
  grep -oE "QA_VERDICT: *(PASS|WARN|FAIL)" "$OUTPUT_FILE" | tail -1 | grep -oE "PASS|WARN|FAIL" || true
}

run_opencode() { # one attempt; returns 0 if the run streamed, 3 if hung
  pkill -9 opencode 2>/dev/null || true
  local marker
  marker=$(wc -l < "$OPENCODE_LOG" 2>/dev/null || echo 0)
  timeout "$RUN_TIMEOUT_SECS" opencode run --agent plan "$(cat "$PROMPT_FILE")" \
    > "$OUTPUT_FILE" 2> "$OUTPUT_FILE.log" &
  local pid=$!
  local waited=0
  while [ "$waited" -lt "$STREAM_WAIT_SECS" ]; do
    if tail -n +"$((marker + 1))" "$OPENCODE_LOG" 2>/dev/null | grep -q "stream providerID"; then
      wait "$pid" || true
      return 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" || true
      return 0 # finished fast (small prompt) — let verdict check decide
    fi
    sleep 5
    waited=$((waited + 5))
  done
  echo "WARN: opencode never reached streaming after ${STREAM_WAIT_SECS}s — killing (hung-at-init signature)" >&2
  kill -9 "$pid" 2>/dev/null || true
  pkill -9 opencode 2>/dev/null || true
  return 3
}

run_codex() {
  timeout "$RUN_TIMEOUT_SECS" codex exec --sandbox read-only --skip-git-repo-check \
    -C "$REPO_ROOT" - < "$PROMPT_FILE" > "$OUTPUT_FILE" 2> "$OUTPUT_FILE.log" || true
}

run_cursor() {
  timeout "$RUN_TIMEOUT_SECS" cursor-agent --print "$(cat "$PROMPT_FILE")" \
    > "$OUTPUT_FILE" 2> "$OUTPUT_FILE.log" || true
}

main() {
  local tool
  tool=$(pick_tool)
  [ "$tool" = "none" ] && { echo "ERROR: no external QA CLI found (opencode/codex/cursor-agent)" >&2; exit 3; }
  echo "external-qa: tool=$tool prompt=$PROMPT_FILE" >&2

  case "$tool" in
    opencode)
      if ! run_opencode; then
        echo "external-qa: retrying once after hung launch" >&2
        run_opencode || { echo "ERROR: opencode hung twice" >&2; exit 3; }
      fi
      ;;
    codex) run_codex ;;
    cursor-agent | cursor) run_cursor ;;
  esac

  strip_ansi "$OUTPUT_FILE"
  local verdict
  verdict=$(extract_verdict)
  case "$verdict" in
    PASS) echo "QA_VERDICT: PASS"; exit 0 ;;
    WARN) echo "QA_VERDICT: WARN"; exit 10 ;;
    FAIL) echo "QA_VERDICT: FAIL"; exit 20 ;;
    *)
      echo "ERROR: no QA_VERDICT line in output (run died mid-stream?) — see $OUTPUT_FILE and $OUTPUT_FILE.log" >&2
      exit 2
      ;;
  esac
}

main
