#!/usr/bin/env bash
# Deterministic LOC baseline for the modularization plan (AE-0077).
#
# Classification rules:
#   tests      = path contains /__tests__/ or starts with src/test/, or
#                filename matches *.test.* or *.spec.*
#   stories    = filename matches *.stories.*
#   production = every other *.ts/*.tsx (frontend) or *.py (backend) file
#
# LOC = physical lines (wc -l). Output is sorted and contains no
# timestamps, so two runs on the same tree are byte-identical.
#
# Snapshot semantics: this reports the CURRENT working tree. A committed
# baseline report reflects the tree at its commit; later runs on HEAD
# will legitimately differ as code lands — that is drift, not
# non-determinism. To reproduce a committed baseline exactly, check out
# the commit that produced it.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

fe_files() { # $1: filter (prod|test|story|all)
  find "$ROOT/frontend/src" -type f \( -name '*.ts' -o -name '*.tsx' \) | sort | while read -r f; do
    rel="${f#"$ROOT"/frontend/}"
    case "$rel" in
      *.stories.*) kind=story ;;
      *.test.*|*.spec.*|*/__tests__/*|src/test/*) kind=test ;;
      *) kind=prod ;;
    esac
    if [ "$1" = all ] || [ "$kind" = "$1" ]; then echo "$f"; fi
  done
}

# xargs may split large file lists into batches; `cat | wc -l` stays
# correct across batches where `wc -l | tail -1` would not.
sum_lines() { xargs -r cat 2>/dev/null | wc -l | tr -d ' '; }
count_files() { wc -l | tr -d ' '; }

echo "== Frontend (frontend/src, *.ts|*.tsx) =="
for kind in prod test story; do
  files=$(fe_files "$kind")
  n=$(printf '%s\n' "$files" | sed '/^$/d' | count_files)
  l=$(printf '%s\n' "$files" | sed '/^$/d' | sum_lines)
  echo "$kind: files=$n lines=${l:-0}"
done

echo ""
echo "== Frontend per-feature (production only) =="
for d in "$ROOT"/frontend/src/features/*/; do
  name=$(basename "$d")
  files=$(fe_files prod | grep "/features/$name/" || true)
  n=$(printf '%s\n' "$files" | sed '/^$/d' | count_files)
  l=$(printf '%s\n' "$files" | sed '/^$/d' | sum_lines)
  echo "$name: files=$n lines=${l:-0}"
done

echo ""
echo "== Backend (backend/src, *.py) =="
b_all=$(find "$ROOT/backend/src" -type f -name '*.py' | sort)
echo "production: files=$(printf '%s\n' "$b_all" | count_files) lines=$(printf '%s\n' "$b_all" | sum_lines)"
b_tests=$(find "$ROOT/backend/tests" -type f -name '*.py' | sort)
echo "tests: files=$(printf '%s\n' "$b_tests" | count_files) lines=$(printf '%s\n' "$b_tests" | sum_lines)"
b_car=$(find "$ROOT/backend/src/rag_backend/application/services/carousel" -type f -name '*.py' | sort)
echo "carousel-services subtotal: files=$(printf '%s\n' "$b_car" | count_files) lines=$(printf '%s\n' "$b_car" | sum_lines)"
