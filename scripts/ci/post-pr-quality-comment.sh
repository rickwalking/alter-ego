#!/usr/bin/env bash
# Post a PR summary comment when a quality gate fails (deterministic CI subset).
set -euo pipefail

if [[ -z "${GITHUB_EVENT_PULL_REQUEST_NUMBER:-}" ]]; then
  echo "Not a pull_request event — skipping PR comment."
  exit 0
fi

PROJECT="${1:-quality}"
JOB_NAME="${2:-unknown}"
DETAILS="${3:-See workflow logs for details.}"

BODY=$(cat <<EOF
### ${PROJECT} quality gate failed: \`${JOB_NAME}\`

${DETAILS}

This check is part of the **CI QA subset** (lint, types, tests, security). For full acceptance-criteria and architecture review, run \`/qa-agent\` locally before merge.

See [QA checkpoints](https://github.com/${GITHUB_REPOSITORY}/blob/main/docs/guides/qa-checkpoints.md#7-cicd-quality-gates).
EOF
)

export GH_TOKEN="${GITHUB_TOKEN:-}"
gh pr comment "${GITHUB_EVENT_PULL_REQUEST_NUMBER}" --body "${BODY}"
