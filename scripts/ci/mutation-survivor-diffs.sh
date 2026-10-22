#!/usr/bin/env bash
# =============================================================================
# mutation-survivor-diffs.sh — print and save the diff of every surviving mutant.
#
# The CI mutation job logs only survivor names, and mutation never runs locally
# (AE-0448), so a developer cannot `mutmut show` a survivor. After the mutation
# gate, CI runs this from backend/: it reads the cached results (no mutants are
# re-run) and writes each survivor's diff to stdout and to the output file,
# which the workflow uploads as the `mutmut-survivors` artifact.
#
# Usage (from backend/): bash ../scripts/ci/mutation-survivor-diffs.sh [out-file]
# Locally it SKIPs (77) through the same CI-only guard as the mutation gate.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/lib/mutation_ci_only.sh
source "$ROOT/scripts/lib/mutation_ci_only.sh"
mutation_ci_only || exit $?

OUT="${1:-mutmut-survivors.txt}"
: > "$OUT"

survivors="$(uv run mutmut results 2>/dev/null | sed -n 's/^[[:space:]]*\(.*\): survived$/\1/p')"
count=0
while IFS= read -r name; do
  [[ -z "$name" ]] && continue
  count=$((count + 1))
  {
    echo "=== $name"
    uv run mutmut show "$name"
    echo
  } | tee -a "$OUT"
done <<< "$survivors"
echo "Surviving mutants: $count (diffs in $OUT)"
