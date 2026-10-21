#!/usr/bin/env bash
# =============================================================================
# mutation_ci_only.sh — mutation testing runs in CI only (AE-0448).
#
# Pedro's call: a local mutmut / Stryker run exhausts the dev machine's memory
# (OOM), so agents and people read the mutation verdict from the CI job on the
# PR head instead of reproducing it. Every local entry point (gates.sh
# backend:mutation / frontend:mutation, mutation-score-gate.sh, `npm run
# test:mutate`) calls this guard BEFORE starting mutmut / Stryker.
#
# Behaviour:
#   GITHUB_ACTIONS=true      -> pass (0): CI runs mutation with its thresholds.
#   ALLOW_LOCAL_MUTATION=1   -> pass (0): explicit opt-in for a machine that has
#                               the memory.
#   anything else            -> one-line message on stderr, return EXIT_SKIP (77)
#                               so run_gate reports SKIP locally (and FAIL under
#                               GATES_REQUIRE_ALL=1, which CI sets).
#
# Usage:
#   source "$REPO_ROOT/scripts/lib/mutation_ci_only.sh"
#   gate() { mutation_ci_only || return $?; ...run mutmut/stryker... }
# or executed directly (exits 0 or 77), e.g. from an npm script:
#   bash ../scripts/lib/mutation_ci_only.sh && stryker run
# =============================================================================

: "${EXIT_SKIP:=77}"

MUTATION_CI_ONLY_MESSAGE="SKIP: mutation runs in CI only (local mutmut/Stryker runs out of memory); read the 'backend / Mutation (blocking ≥75%)' and 'frontend / Mutation (advisory)' results for this commit with \`gh pr checks <pr>\` / \`gh run view <run-id> --log\` (set ALLOW_LOCAL_MUTATION=1 to run it here anyway)."

mutation_ci_only() {
  [[ "${GITHUB_ACTIONS:-}" == "true" ]] && return 0
  [[ "${ALLOW_LOCAL_MUTATION:-}" == "1" ]] && return 0
  echo "$MUTATION_CI_ONLY_MESSAGE" >&2
  return "$EXIT_SKIP"
}

# Executed (not sourced): act as a standalone guard and exit with its status.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  mutation_ci_only
  exit $?
fi
