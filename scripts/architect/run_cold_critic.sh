#!/usr/bin/env bash
# Prepare blind review packet for external LLM (manual invocation).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TICKET_ID="${1:-}"
if [[ -z "$TICKET_ID" ]]; then
  echo "Usage: $0 AE-####" >&2
  exit 1
fi
PLAN="$ROOT/.agent/reports/${TICKET_ID}.arch-plan.md"
PROMPT="$ROOT/skills/architect-skill/prompts/cold-critic-system.md"
OUT="$ROOT/.agent/reports/${TICKET_ID}.skeptical-review.md"
if [[ ! -f "$PLAN" ]]; then
  echo "Missing arch plan: $PLAN" >&2
  exit 1
fi
echo "=== Cold critic packet ==="
echo "System prompt: $PROMPT"
echo "Plan: $PLAN"
echo "Save external output to: $OUT"
echo ""
cat "$PROMPT"
echo ""
echo "=== PLAN ==="
cat "$PLAN"
