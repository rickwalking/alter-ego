#!/usr/bin/env bash
# Run strict ruff rules (complexity, args) on backend files changed vs main.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT/backend"

mapfile -t FILES < <("$SCRIPT_DIR/changed-backend-files.sh")
SRC_FILES=()
for file in "${FILES[@]}"; do
  if [[ "$file" == src/* ]]; then
    SRC_FILES+=("$file")
  fi
done

if ((${#SRC_FILES[@]} == 0)); then
  echo "No changed backend source files — skipping strict diff ruff."
  exit 0
fi

echo "Strict ruff on ${#SRC_FILES[@]} changed source file(s): PLR0913, C901, PLR0912"
uv run ruff check \
  --isolated \
  --target-version py311 \
  --select PLR0913,C901,PLR0912 \
  --config lint.pylint.max-args=3 \
  --config lint.pylint.max-branches=8 \
  --config lint.mccabe.max-complexity=10 \
  "${SRC_FILES[@]}"
