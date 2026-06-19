#!/usr/bin/env bash
# =============================================================================
# require_tool.sh — preflight that tells "tool not installed" apart from a real
# violation, for the tool-dependent frontend quality gates (AE-0239).
#
# Problem: frontend gates shell out to jscpd / knip. When those binaries are
# absent locally they exit 127, and gates.sh maps any unrecognised exit to FAIL,
# so a clean tree reads as broken (and an advisory gate that swallows the 127 with
# `|| echo` reads as a false PASS). Both hide signal.
#
# Resolution: probe `node_modules/.bin/<tool>` directly (NOT `which`/`command -v`,
# which miss npm-local binaries; NOT `npx`, which would auto-install and defeat the
# check). On a miss, emit an actionable message and return EXIT_SKIP (77) so
# run_gate reports SKIP locally — and FAIL under GATES_REQUIRE_ALL=1 (CI installs
# the tools via `npm ci`, so a miss there genuinely IS a failure).
#
# Usage (source it, then call the helper):
#   source "$REPO_ROOT/scripts/lib/require_tool.sh"
#   gate() { require_tool jscpd || return $?; ...run the tool... }
#
# Inputs (env, with safe defaults so the lib is sourceable standalone in tests):
#   FRONTEND_BIN_DIR  dir holding the npm-local binaries (default: empty => miss)
#   EXIT_SKIP         skip exit code (default: 77, matching gates.sh)
# =============================================================================

: "${EXIT_SKIP:=77}"
: "${FRONTEND_BIN_DIR:=}"

require_tool() {
  local tool="$1"
  [[ -n "$FRONTEND_BIN_DIR" && -x "$FRONTEND_BIN_DIR/$tool" ]] && return 0
  echo "devDependency '$tool' not installed — run \`cd frontend && npm ci\`" >&2
  return "$EXIT_SKIP"
}
