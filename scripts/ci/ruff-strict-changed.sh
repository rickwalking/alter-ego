#!/usr/bin/env bash
# Run strict ruff rules (complexity, args) on lines changed vs main.
# Only fails on violations IN the diff, not pre-existing ones in untouched code.
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
  uv run ruff check \
    --isolated \
    --target-version py311 \
    --select PLR0913,C901,PLR0912 \
    --config lint.pylint.max-args=3 \
    --config lint.pylint.max-branches=8 \
    --config lint.mccabe.max-complexity=10 \
    "$file" 2>/dev/null | while IFS= read -r line; do
      # Extract line number from ruff output (format: "file:line:col: code message")
      if [[ "$line" =~ ^([^:]+):([0-9]+): ]]; then
        vline="${BASH_REMATCH[2]}"
        in_diff=false
        while IFS= read -r r; do
          start_line="${r%%:*}"
          count="${r##*:}"
          if [ "$count" -eq 0 ]; then count=1; fi
          end_line=$((start_line + count - 1))
          if [ "$vline" -ge "$start_line" ] 2>/dev/null && [ "$vline" -le "$end_line" ] 2>/dev/null; then
            in_diff=true
            break
          fi
        done <<< "$(echo "$changed" | tr ' ' '\n')"

        if [ "$in_diff" = true ]; then
          echo "$line"
          EXIT_CODE=1
        fi
      fi
    done
done

rm -f "$TEMP_OUTPUT"

if [ "$EXIT_CODE" -ne 0 ]; then
  echo "Strict diff: violations found in changed lines."
fi
exit "$EXIT_CODE"
