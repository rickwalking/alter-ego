#!/usr/bin/env bash
# =============================================================================
# diff_base.sh — shared diff-base resolver for every diff-scoped quality gate.
#
# Problem (AE-0177): diff-scoped gates hand-rolled `git diff BASE...HEAD` (the
# merge-base form). On a stacked branch, or when `origin/main` has diverged so
# there is no merge base, that form fails with `fatal: no merge base` and — when
# the caller swallowed stderr with `2>/dev/null` — silently degraded the gate to
# a no-op (it saw zero changed files and "passed"). A gate that silently passes
# is worse than no gate.
#
# This is the bash port of the proven 3-tier fallback that already lives in
# frontend/scripts/check-dead-code.mjs (changedFrontendFiles):
#   1. merge-base form   `BASE...HEAD`   (normal PR vs a shared base)
#   2. two-ref form      `BASE HEAD`     (stacked branch / diverged base: no merge base)
#   3. advisory          (neither resolves) — emit a VISIBLE warning to stderr and
#                        signal the caller to degrade to advisory, NEVER a silent pass.
#
# Usage (source it, then call the helpers):
#   source "$REPO_ROOT/scripts/lib/diff_base.sh"
#   if range="$(resolve_diff_base "origin/main")"; then
#     git diff --name-only $range -- <pathspec>     # $range is unquoted on purpose
#   else
#     : # advisory: warning already emitted to stderr; do not block
#   fi
#
# `resolve_diff_base` echoes the resolved range token(s) on stdout:
#   tier 1 -> "BASE...HEAD"     (single token)
#   tier 2 -> "BASE HEAD"       (two tokens; rely on word-splitting at the call site)
# and returns 0. On tier 3 it echoes nothing, warns on stderr, and returns 1.
# =============================================================================

# Resolve the diff range for BASE..HEAD using the 3-tier fallback.
# Echoes the range token(s) and returns 0; returns 1 (advisory) when neither
# the merge-base nor the two-ref form is usable.
resolve_diff_base() {
  local base="${1:?resolve_diff_base requires a base ref}"

  # Tier 1: merge-base form. Requires a merge base to exist.
  if git merge-base "$base" HEAD >/dev/null 2>&1; then
    printf '%s...HEAD' "$base"
    return 0
  fi

  # Tier 2: two-ref form. Works on a stacked branch with no merge base, as long
  # as the base ref itself is resolvable.
  if git rev-parse --verify --quiet "$base" >/dev/null 2>&1; then
    printf 'WARNING: no merge base between %s and HEAD; ' "$base" >&2
    printf 'falling back to the two-ref diff (%s HEAD).\n' "$base" >&2
    printf '%s HEAD' "$base"
    return 0
  fi

  # Tier 3: advisory. Neither form resolves — warn loudly, never pass silently.
  printf 'WARNING: cannot resolve diff base %q (no merge base and ref is ' "$base" >&2
  printf 'unresolvable); this diff-scoped gate degrades to ADVISORY this run ' >&2
  printf '(no changed-file enforcement). This is NOT a pass.\n' >&2
  return 1
}

# Convenience: list changed file names vs BASE using the resolved range.
# Args: <base_ref> [-- pathspec...]. Echoes names on stdout (may be empty).
# Returns 0 when the base resolved (tier 1/2), 1 when it degraded to advisory.
diff_base_names() {
  local base="${1:?diff_base_names requires a base ref}"; shift
  local range
  if ! range="$(resolve_diff_base "$base")"; then
    return 1
  fi
  # shellcheck disable=SC2086 # $range must word-split into one or two refs.
  git diff --name-only --diff-filter=ACMRT $range "$@"
  return 0
}
