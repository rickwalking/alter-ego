#!/usr/bin/env bash
# =============================================================================
# external_agent_guard_check.sh (AE-0170) — self-contained verification that
# ext_run_guarded isolates external runs in a worktree and detects/restores a
# rogue HEAD-detach / branch-move of the primary repo. Exits 0 on success.
# Run directly or via the vitest wrapper (frontend/src/scripts/external-guard.test.ts).
# =============================================================================
set -uo pipefail

LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/external_agent.sh"
PRIMARY="$(mktemp -d "${TMPDIR:-/tmp}/ext-guard-primary.XXXXXX")"
trap 'rm -rf "$PRIMARY"' EXIT

git -C "$PRIMARY" init -q -b main
git -C "$PRIMARY" config user.email t@t.dev
git -C "$PRIMARY" config user.name tester
echo one > "$PRIMARY/f"; git -C "$PRIMARY" add f; git -C "$PRIMARY" commit -qm one
echo two >> "$PRIMARY/f"; git -C "$PRIMARY" commit -qam two

# shellcheck source=external_agent.sh
. "$LIB"
EXT_REPO_ROOT="$PRIMARY"
HEAD0="$(git -C "$PRIMARY" rev-parse HEAD)"
out="$PRIMARY/out"

fail() { echo "GUARD-CHECK FAIL: $1" >&2; exit 1; }

# --- A) clean run: returns 0, primary unchanged, no leaked worktree ----------
ext_run() { echo "clean output" > "$3"; return 0; }
ext_run_guarded fake /dev/null "$out"; rc=$?
[ "$rc" = 0 ] || fail "clean run rc=$rc (expected 0)"
[ "$(git -C "$PRIMARY" rev-parse HEAD)" = "$HEAD0" ] || fail "clean run moved HEAD"
[ "$(git -C "$PRIMARY" rev-parse --abbrev-ref HEAD)" = "main" ] || fail "clean run changed branch"
git -C "$PRIMARY" worktree list | grep -q "ext-wt" && fail "worktree leaked after clean run"
[ -f "$out" ] || fail "clean run produced no output file"

# --- B) rogue detach: guard trips (rc 4) and restores main@HEAD0 -------------
ext_run() { git -C "$PRIMARY" checkout -q --detach HEAD~1; echo "rogue" > "$3"; return 0; }
ext_run_guarded fake /dev/null "$out"; rc=$?
[ "$rc" = 4 ] || fail "rogue detach not caught (rc=$rc, expected 4)"
[ "$(git -C "$PRIMARY" rev-parse --abbrev-ref HEAD)" = "main" ] || fail "primary not restored to main"
[ "$(git -C "$PRIMARY" rev-parse HEAD)" = "$HEAD0" ] || fail "primary HEAD not restored"
git -C "$PRIMARY" worktree list | grep -q "ext-wt" && fail "worktree leaked after rogue run"

echo "external_agent guard-check OK (isolation + detach-detect/restore + cleanup)."
