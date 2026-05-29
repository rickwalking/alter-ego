#!/usr/bin/env bash
# Pipe ruff output to reviewdog for inline PR comments.
set -euo pipefail

RUFF_ARGS=("$@")
if ((${#RUFF_ARGS[@]} == 0)); then
  RUFF_ARGS=(check src/)
fi

uv run ruff "${RUFF_ARGS[@]}" --output-format=rdjson \
  | reviewdog -f=rdjson -name=ruff -reporter=github-pr-review -level=error -filter-mode=diff_context \
  || true
