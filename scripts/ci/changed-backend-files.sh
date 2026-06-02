#!/usr/bin/env bash
# List changed backend Python files for diff-scoped quality gates.
set -euo pipefail

BASE_REF="${1:-origin/main}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT"
git fetch origin main --depth=1 2>/dev/null || true

mapfile -t FILES < <(
  git diff --name-only --diff-filter=ACMRT "${BASE_REF}"...HEAD -- 'backend/src/**/*.py' 'backend/tests/**/*.py' 2>/dev/null \
    | sed 's|^backend/||' \
    | sort -u
)

if ((${#FILES[@]} == 0)); then
  exit 0
fi

printf '%s\n' "${FILES[@]}"
