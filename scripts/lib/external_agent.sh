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
#   EXT_OPENCODE_MODEL          default opencode-go/glm-5.2 (AE-0292)
#     Funded routes (keep this list current): opencode-go/glm-5.2.
#     Do NOT use opencode/glm-5.2 — that is the Zen route opencode resolves to
#     WITHOUT -m, and it dies with "Insufficient balance". Reasoning runs take
#     3-8 min: run in background, redirect stdin from /dev/null.
# =============================================================================

EXT_OPENCODE_LOG="${EXT_OPENCODE_LOG:-$HOME/.local/share/opencode/log/opencode.log}"
EXT_STREAM_WAIT_SECS="${EXTERNAL_STREAM_WAIT_SECS:-90}"
EXT_RUN_TIMEOUT_SECS="${EXTERNAL_RUN_TIMEOUT_SECS:-${QA_RUN_TIMEOUT_SECS:-1500}}"
EXT_OPENCODE_MODEL="${EXT_OPENCODE_MODEL:-opencode-go/glm-5.2}"

# Preamble for the engagement-retry (AE-0292): reasoning models sometimes go
# agentic (tool-hunting) under the plan agent and stream NOTHING back; the
# retry pins them to plain analysis. Distinct exit code so callers can react
# (e.g. fall back to codex) instead of accepting a silent empty verdict.
EXT_NO_TOOLS_PREAMBLE="IMPORTANT: do NOT use tools. Respond with analysis only."
EXT_EXIT_EMPTY_OUTPUT=5

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
  # -m pins the FUNDED route (AE-0292): without it opencode's plan agent
  # resolves to the unfunded Zen glm-5.2 and dies with "Insufficient balance".
  timeout "$EXT_RUN_TIMEOUT_SECS" opencode run -m "$EXT_OPENCODE_MODEL" --agent plan \
    "$(cat "$prompt_file")" \
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

# ext_output_engaged <output-file> -> 0 if the file has non-whitespace content.
ext_output_engaged() {
  [ -s "$1" ] && grep -q '[^[:space:]]' "$1"
}

# _ext_opencode_engaged <prompt-file> <output-file>  (AE-0292)
#   Runs OpenCode (with the hung-launch retry) and then applies the engagement
#   sanity check: an empty/whitespace-only reply gets ONE retry with the
#   no-tools preamble prepended; a second empty reply is a hard failure with a
#   distinct exit code (EXT_EXIT_EMPTY_OUTPUT) so the caller can fall back to
#   another tool instead of accepting a silent empty verdict.
_ext_opencode_engaged() {
  local prompt_file="$1" output_file="$2"
  if ! _ext_run_opencode "$prompt_file" "$output_file"; then
    echo "external-agent: retrying once after hung launch" >&2
    _ext_run_opencode "$prompt_file" "$output_file" || {
      echo "ERROR: opencode hung twice" >&2; return 3; }
  fi
  ext_output_engaged "$output_file" && return 0

  echo "WARN: opencode returned empty output — retrying once with the no-tools preamble (AE-0292)" >&2
  local preamble_prompt="$output_file.no-tools-prompt"
  { echo "$EXT_NO_TOOLS_PREAMBLE"; echo; cat "$prompt_file"; } > "$preamble_prompt"
  if ! _ext_run_opencode "$preamble_prompt" "$output_file"; then
    echo "ERROR: opencode hung on the engagement retry" >&2; return 3
  fi
  ext_output_engaged "$output_file" && return 0
  echo "ERROR: opencode produced empty output twice — engagement failure (AE-0292)" >&2
  return "$EXT_EXIT_EMPTY_OUTPUT"
}

# ext_run <tool> <prompt-file> <output-file>
#   Runs the prompt; for OpenCode retries once on a hung launch and once on an
#   empty (non-engaged) reply.
#   Returns 0 on a run that produced output, 3 on launch failure / double-hang,
#   EXT_EXIT_EMPTY_OUTPUT (5) on a double-empty OpenCode reply.
ext_run() {
  local tool="$1" prompt_file="$2" output_file="$3"
  echo "external-agent: tool=$tool prompt=$prompt_file" >&2
  case "$tool" in
    opencode)            _ext_opencode_engaged "$prompt_file" "$output_file" || return $? ;;
    codex)               _ext_run_codex "$prompt_file" "$output_file" ;;
    cursor-agent|cursor) _ext_run_cursor "$prompt_file" "$output_file" ;;
    none|*) echo "ERROR: no external CLI available (opencode/codex/cursor-agent)" >&2; return 3 ;;
  esac
  return 0
}

# ext_run_guarded <tool> <prompt-file> <output-file>  (AE-0170)
#   Runs the external (non-sandboxed) CLI inside a throwaway, DETACHED git
#   worktree so it cannot mutate the primary working tree or move the working
#   branch, and ABORTS if the primary repo's HEAD, branch, OR working-tree status
#   changed during the run (the rogue-detach / off-branch-commit incident). HEAD
#   and branch are restored on a trip; a working-tree change is reported and trips
#   the guard but is NOT auto-reverted (it could be the operator's legitimate
#   uncommitted work). The worktree is auto-cleaned. The external run's /tmp
#   <output-file> stays authoritative.
#   Returns: ext_run's rc, 3 on worktree-setup failure, or 4 on a tripped guard.
ext_run_guarded() {
  local tool="$1" prompt_file="$2" output_file="$3"
  local primary="$EXT_REPO_ROOT"
  local head_before branch_before status_before
  head_before="$(git -C "$primary" rev-parse HEAD 2>/dev/null)"
  branch_before="$(git -C "$primary" rev-parse --abbrev-ref HEAD 2>/dev/null)"
  status_before="$(git -C "$primary" status --porcelain 2>/dev/null)"

  local wt
  wt="$(mktemp -d "${TMPDIR:-/tmp}/ext-wt.XXXXXX")"
  if ! git -C "$primary" worktree add --quiet --detach "$wt" HEAD 2>"$output_file.wt.log"; then
    echo "ERROR: could not create isolated worktree (AE-0170):" >&2
    cat "$output_file.wt.log" >&2
    rmdir "$wt" 2>/dev/null || true
    return 3
  fi

  # Run the CLI with the worktree as both cwd and repo root.
  local rc
  EXT_REPO_ROOT="$wt"
  ( cd "$wt" && ext_run "$tool" "$prompt_file" "$output_file" )
  rc=$?
  EXT_REPO_ROOT="$primary"

  # Auto-clean: --force because the tool may have left rogue/untracked files.
  git -C "$primary" worktree remove --force "$wt" 2>/dev/null || rm -rf "$wt"
  git -C "$primary" worktree prune 2>/dev/null || true

  # Guard: the PRIMARY repo's HEAD, branch, and working-tree status must be
  # exactly as before.
  local head_after branch_after status_after
  head_after="$(git -C "$primary" rev-parse HEAD 2>/dev/null)"
  branch_after="$(git -C "$primary" rev-parse --abbrev-ref HEAD 2>/dev/null)"
  status_after="$(git -C "$primary" status --porcelain 2>/dev/null)"
  if [ "$head_after" != "$head_before" ] || [ "$branch_after" != "$branch_before" ]; then
    echo "FATAL: primary git HEAD/branch changed during the external run (AE-0170 guard):" >&2
    echo "  before=${branch_before}@${head_before}  after=${branch_after}@${head_after}" >&2
    if [ "$branch_before" != "HEAD" ]; then
      git -C "$primary" checkout --quiet --force "$branch_before" 2>/dev/null || true
    fi
    git -C "$primary" reset --hard --quiet "$head_before" 2>/dev/null || true
    return 4
  fi
  if [ "$status_after" != "$status_before" ]; then
    echo "FATAL: primary working tree changed during the external run (AE-0170 guard)." >&2
    echo "  Inspect with 'git -C \"$primary\" status'; not auto-reverted." >&2
    return 4
  fi
  return "$rc"
}
