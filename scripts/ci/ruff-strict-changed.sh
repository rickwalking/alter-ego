#!/usr/bin/env bash
# Run strict ruff rules (complexity, args) on lines changed vs main.
# Only fails on violations IN the diff, not pre-existing ones in untouched code.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT/backend"

# AE-0080: composition-root app factory was relocated byte-identical from
# api/app.py (which the diff gate never flagged because it predates the diff)
# to bootstrap/app_factory.py. The relocation made the moved file "changed",
# exposing its intrinsic composition-root branchiness (PLR0911 etc.) to this
# isolated diff gate. Refactoring the moved code would break the AE-0080
# no-behavior-change guarantee, so the composition root is exempted here —
# mirroring the per-file ignore in backend/pyproject.toml that already
# exempts the same file for the config-aware `ruff check src/` gate. A NEW
# real violation in any other file still fails this gate.
STRICT_DIFF_EXEMPT=(
  "src/rag_backend/bootstrap/app_factory.py"
)

is_exempt() {
  local candidate="$1"
  local exempt
  for exempt in "${STRICT_DIFF_EXEMPT[@]}"; do
    if [[ "$candidate" == "$exempt" ]]; then
      return 0
    fi
  done
  return 1
}

mapfile -t FILES < <("$SCRIPT_DIR/changed-backend-files.sh")
SRC_FILES=()
for file in "${FILES[@]}"; do
  if [[ "$file" == src/* ]] && ! is_exempt "$file"; then
    SRC_FILES+=("$file")
  fi
done

if ((${#SRC_FILES[@]} == 0)); then
  echo "No changed backend source files — skipping strict diff ruff."
  exit 0
fi

echo "Strict ruff on ${#SRC_FILES[@]} changed source file(s): PLR0913, C901, PLR0912, PLR0911, PLR0914, PLR1702"

# Collect changed line ranges from git diff for each file
declare -A CHANGED_LINES
for file in "${SRC_FILES[@]}"; do
  key=$(echo "$file" | tr / _)
  # Get added lines from the diff (unified=0 to skip context)
  CHANGED_LINES["$key"]=$(git diff -U0 origin/main...HEAD -- "$file" 2>/dev/null | grep -E '^@@' | sed 's/^@@ -[0-9,]* +\([0-9]*\),\?\([0-9]*\) @@.*/\1:\2/')
done

# Run ruff on each file and filter violations to only those on changed lines
EXIT_CODE=0
TEMP_OUTPUT=$(mktemp)
for file in "${SRC_FILES[@]}"; do
  key=$(echo "$file" | tr / _)
  changed="${CHANGED_LINES[$key]:-}"

  if [ -z "$changed" ]; then
    continue
  fi

  # Run ruff on single file and capture violation lines
  # NOTE: redirect ruff output to temp file to decouple its exit code from
  # the while loop — ruff exits 1 when violations exist, which with
  # set -eo pipefail would abort the loop before processing violations.
  # AE-0049 thresholds: max-args=3, max-complexity=10, max-branches=8,
  # max-returns=5, max-locals=12, max-nested-blocks=4.
  uv run ruff check \
    --isolated \
    --target-version py311 \
    --select PLR0913,C901,PLR0912,PLR0911,PLR0914,PLR1702 \
    --config lint.pylint.max-args=3 \
    --config lint.pylint.max-branches=8 \
    --config lint.pylint.max-returns=5 \
    --config lint.pylint.max-locals=12 \
    --config lint.pylint.max-nested-blocks=4 \
    --config lint.mccabe.max-complexity=10 \
    "$file" 2>/dev/null > "$TEMP_OUTPUT" || true
  while IFS= read -r line; do
    # Extract line number from ruff output (format: "file:line:col: code message")
    if [[ "$line" =~ ^([^:]+):([0-9]+): ]]; then
      vline="${BASH_REMATCH[2]}"
      in_diff=false
      while IFS= read -r r; do
        start_line="${r%%:*}"
        count="${r##*:}"
        if [ -z "$count" ] || [ "$count" -eq 0 ]; then count=1; fi
        end_line=$((start_line + count - 1))
        if [ -n "$start_line" ] && [ "$vline" -ge "$start_line" ] 2>/dev/null && [ "$vline" -le "$end_line" ] 2>/dev/null; then
          in_diff=true
          break
        fi
      done <<< "$(echo "$changed" | tr ' ' '\n')"

      if [ "$in_diff" = true ]; then
        echo "$line"
        EXIT_CODE=1
      fi
    fi
  done < "$TEMP_OUTPUT"
done

rm -f "$TEMP_OUTPUT"

if [ "$EXIT_CODE" -ne 0 ]; then
  echo "Strict diff: violations found in changed lines."
fi
exit "$EXIT_CODE"
