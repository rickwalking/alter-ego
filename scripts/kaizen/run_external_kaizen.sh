#!/usr/bin/env bash
# External Kaizen orchestrator (kaizen-skill).
#
# Offloads the token-heavy ANALYSIS phases (Phase 0 signal gather, Phase 1
# research pack, Phase 2 root-cause + rule-mapping) to a cheaper external LLM
# CLI, using the shared hardened mechanics in scripts/lib/external_agent.sh.
# The external run is READ-ONLY: it writes the improvement plan to <output-file>
# and ends with a machine-readable KAIZEN_JSON proposals block.
#
# The MAIN session still owns the trusted/judgment steps:
#   - re-validate the ratchet invariant on every returned proposal
#     (NEVER trust the external model to self-police it),
#   - the human approval gate (Phase 4),
#   - ticket emission (Phase 5, writes the repo).
#
# Usage:
#   scripts/kaizen/run_external_kaizen.sh <prompt-file> <output-file> [tool]
#
# Exit codes: 0=plan + proposals produced, 2=no proposals block (run died?),
#             3=launch failed after retry.
set -euo pipefail

PROMPT_FILE="${1:?usage: run_external_kaizen.sh <prompt-file> <output-file> [tool]}"
OUTPUT_FILE="${2:?usage: run_external_kaizen.sh <prompt-file> <output-file> [tool]}"
TOOL="${3:-opencode}"

# shellcheck source=../lib/external_agent.sh
. "$(cd "$(dirname "$0")/../lib" && pwd)/external_agent.sh"

# Extract the last fenced ```json block containing a "proposals" key to
# <output>.proposals.json so the main session can re-validate + emit tickets.
extract_proposals_json() {
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$OUTPUT_FILE" "$OUTPUT_FILE.proposals.json" <<'PY'
import json, re, sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8", errors="replace").read()
blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
chosen = None
for b in blocks:
    try:
        obj = json.loads(b)
    except Exception:
        continue
    if isinstance(obj, dict) and "proposals" in obj:
        chosen = obj
if chosen is None:
    sys.exit(1)
json.dump(chosen, open(dst, "w", encoding="utf-8"), indent=2)
PY
}

main() {
  local tool
  tool=$(ext_pick_tool "$TOOL")
  [ "$tool" = "none" ] && { echo "ERROR: no external kaizen CLI found (opencode/codex/cursor-agent)" >&2; exit 3; }

  ext_run_guarded "$tool" "$PROMPT_FILE" "$OUTPUT_FILE" || exit 3

  ext_strip_ansi "$OUTPUT_FILE"
  if extract_proposals_json; then
    echo "KAIZEN: proposals extracted -> $OUTPUT_FILE.proposals.json"
    echo "NOTE: main session must re-validate the ratchet invariant before approval/emission."
    exit 0
  fi
  echo "ERROR: no KAIZEN_JSON proposals block in output (run died mid-stream?) — see $OUTPUT_FILE and $OUTPUT_FILE.log" >&2
  exit 2
}

main
