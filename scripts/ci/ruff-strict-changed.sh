#!/usr/bin/env bash
# Run strict ruff rules (complexity, args) on backend files changed vs main.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT/backend"

mapfile -t FILES < <("$SCRIPT_DIR/changed-backend-files.sh")

if ((${#FILES[@]} == 0)); then
  echo "No changed backend Python files — skipping strict diff ruff."
  exit 0
fi

echo "Strict ruff on ${#FILES[@]} changed file(s): PLR0913, C901, PLR0912"
uv run ruff check --select PLR0913,C901,PLR0912 "${FILES[@]}"
