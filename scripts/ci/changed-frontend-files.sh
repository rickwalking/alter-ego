#!/usr/bin/env bash
# List changed frontend TypeScript files for diff-scoped quality gates.
set -euo pipefail

BASE_REF="${1:-origin/main}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT"
git fetch origin main --depth=1 2>/dev/null || true

mapfile -t FILES < <(
  git diff --name-only --diff-filter=ACMRT "${BASE_REF}"...HEAD -- 'frontend/src/**/*.ts' 'frontend/src/**/*.tsx' 2>/dev/null \
    | sed 's|^frontend/||' \
    | sort -u
)

if ((${#FILES[@]} == 0)); then
  exit 0
fi

printf '%s\n' "${FILES[@]}"
