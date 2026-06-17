#!/usr/bin/env bash
# List changed backend Python files for diff-scoped quality gates.
# Uses the shared 3-tier diff-base resolver (AE-0177): merge-base -> two-ref ->
# advisory-with-warning, so a missing merge base never silently no-ops the gate.
set -euo pipefail

BASE_REF="${1:-origin/main}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/lib/diff_base.sh
source "$ROOT/scripts/lib/diff_base.sh"

cd "$ROOT"
git fetch origin main --depth=1 2>/dev/null || true

# Resolve the range first so a tier-3 advisory degrade is detectable (a pipe
# would hide the resolver's exit status). The resolver warns on stderr; on
# advisory we emit no file list (callers skip on empty), never a silent pass.
if ! RANGE="$(resolve_diff_base "$BASE_REF")"; then
  exit 0
fi

# shellcheck disable=SC2086 # $RANGE word-splits into one or two refs by design.
mapfile -t FILES < <(
  git diff --name-only --diff-filter=ACMRT $RANGE -- \
    'backend/src/**/*.py' 'backend/tests/**/*.py' \
    | sed 's|^backend/||' \
    | sort -u
)

if ((${#FILES[@]} == 0)); then
  exit 0
fi

printf '%s\n' "${FILES[@]}"
