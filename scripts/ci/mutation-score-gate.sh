#!/usr/bin/env bash
# Mutation-score gate (AE-0049).
#
# Runs mutmut, exports the CI/CD stats JSON, computes the mutation score, and
# fails if it drops below the threshold. mutmut 3.x has no built-in
# --fail-under, so we derive the score from `mutmut export-cicd-stats`.
#
# Score = killed / (killed + survived + timeout + suspicious)
# (skipped / no_tests mutants are excluded — they were never executed and so
#  cannot be killed; counting them would understate the score artificially).
#
# Usage: mutation-score-gate.sh [THRESHOLD]
#   THRESHOLD  Minimum acceptable score as a percentage (default: 75).
set -euo pipefail

THRESHOLD="${1:-75}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATS_FILE="$ROOT/backend/mutants/mutmut-cicd-stats.json"

cd "$ROOT/backend"

echo "Running mutation tests (mutmut)…"
uv run mutmut run || true   # mutmut exits non-zero when mutants survive; the
                            # gate below is what decides pass/fail.

echo "Exporting mutation stats…"
uv run mutmut export-cicd-stats

if [ ! -f "$STATS_FILE" ]; then
  echo "ERROR: mutation stats file not found at $STATS_FILE" >&2
  exit 1
fi

SCORE="$(
  python3 - "$STATS_FILE" <<'PY'
import json
import sys

with open(sys.argv[1]) as fh:
    data = json.load(fh)

killed = data.get("killed", 0)
survived = data.get("survived", 0)
timeout = data.get("timeout", 0)
suspicious = data.get("suspicious", 0)

denominator = killed + survived + timeout + suspicious
if denominator == 0:
    print("0.0")
else:
    print(f"{killed / denominator * 100:.2f}")
PY
)"

echo "Mutation score: ${SCORE}% (threshold: ${THRESHOLD}%)"

if python3 -c "import sys; sys.exit(0 if float('${SCORE}') >= float('${THRESHOLD}') else 1)"; then
  echo "PASS: mutation score ${SCORE}% meets the ${THRESHOLD}% threshold."
  exit 0
fi

cat >&2 <<EOF
FAIL: mutation score ${SCORE}% is below the ${THRESHOLD}% threshold.

To fix:
  1. Inspect surviving mutants:   cd backend && uv run mutmut results
  2. Show a specific mutant:       cd backend && uv run mutmut show <id>
  3. Strengthen the test that should have killed it (add/assert behavior).
  4. Re-run locally:               bash scripts/ci/mutation-score-gate.sh ${THRESHOLD}

See docs/decisions/0005-adopt-mutation-testing.md for thresholds.
EOF
exit 1
