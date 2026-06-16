#!/usr/bin/env bash
# External QA orchestrator (qa-agent skill).
#
# Runs a QA prompt through an external LLM CLI (OpenCode / Codex / Cursor) using
# the shared, hardened mechanics in scripts/lib/external_agent.sh (tool fallback,
# OpenCode hang-recovery, ANSI strip), then applies the QA-specific output
# contract: QA_VERDICT extraction + optional JSON findings block.
#
# Usage:
#   scripts/qa/run_external_qa.sh <prompt-file> <output-file> [tool]
#
# tool: opencode (default) | codex | cursor — falls back down that list
# if the requested tool is not installed.
#
# Exit codes: 0=PASS, 10=WARN, 20=FAIL, 2=no verdict produced, 3=launch
# failed after retry.
set -euo pipefail

PROMPT_FILE="${1:?usage: run_external_qa.sh <prompt-file> <output-file> [tool]}"
OUTPUT_FILE="${2:?usage: run_external_qa.sh <prompt-file> <output-file> [tool]}"
TOOL="${3:-opencode}"

# shellcheck source=../lib/external_agent.sh
. "$(cd "$(dirname "$0")/../lib" && pwd)/external_agent.sh"

extract_verdict() {
  grep -oE "QA_VERDICT: *(PASS|WARN|FAIL)" "$OUTPUT_FILE" | tail -1 | grep -oE "PASS|WARN|FAIL" || true
}

# Wave-loop fingerprint/plateau detection (developer-skill wave mode) consumes a
# JSON findings block when present. Extract the last fenced ```json ... ``` block
# that parses and contains a "findings" key; write it to <output>.findings.json.
# Best-effort: absence is fine — the loop falls back to text findings.
extract_findings_json() {
  command -v python3 >/dev/null 2>&1 || return 0
  python3 - "$OUTPUT_FILE" "$OUTPUT_FILE.findings.json" <<'PY' 2>/dev/null || true
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
    if isinstance(obj, dict) and "findings" in obj:
        chosen = obj
if chosen is not None:
    json.dump(chosen, open(dst, "w", encoding="utf-8"), indent=2)
PY
}

main() {
  local tool
  tool=$(ext_pick_tool "$TOOL")
  [ "$tool" = "none" ] && { echo "ERROR: no external QA CLI found (opencode/codex/cursor-agent)" >&2; exit 3; }

  ext_run "$tool" "$PROMPT_FILE" "$OUTPUT_FILE" || exit 3

  ext_strip_ansi "$OUTPUT_FILE"
  extract_findings_json
  local verdict
  verdict=$(extract_verdict)
  case "$verdict" in
    PASS) echo "QA_VERDICT: PASS"; exit 0 ;;
    WARN) echo "QA_VERDICT: WARN"; exit 10 ;;
    FAIL) echo "QA_VERDICT: FAIL"; exit 20 ;;
    *)
      echo "ERROR: no QA_VERDICT line in output (run died mid-stream?) — see $OUTPUT_FILE and $OUTPUT_FILE.log" >&2
      exit 2
      ;;
  esac
}

main
