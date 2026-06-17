#!/usr/bin/env bash
# =============================================================================
# check-build-output-ignored.sh (AE-0171) — pre-flight: every documented build /
# coverage output path (scripts/ci/build-outputs.txt) must be gitignored, so a
# stray artifact never breaks eslint/QA (e.g. `npm run build-storybook` writing
# storybook-static/, which broke eslint during AE-0154 until it was gitignored).
#
# A path is "ignored" if `git check-ignore` matches it as a file OR a directory.
# A TRACKED file is never reported ignored by git — so committed artifacts also
# fail here (they must be `git rm --cached`'d + ignored).
#
# Env: BUILD_OUTPUTS_FILE   override the map (testing)
#      BUILD_OUTPUTS_ROOT    override the repo root (testing)
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAP="${BUILD_OUTPUTS_FILE:-$SCRIPT_DIR/build-outputs.txt}"
ROOT="${BUILD_OUTPUTS_ROOT:-$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)}"

[ -f "$MAP" ] || { echo "build-outputs map not found: $MAP" >&2; exit 2; }
cd "$ROOT" || exit 2

fail=0
checked=0
while IFS= read -r line; do
  case "$line" in '' | \#*) continue ;; esac
  path="${line%%[[:space:]#]*}"
  [ -z "$path" ] && continue
  checked=$((checked + 1))
  # Match either a file rule (no slash) or a dir rule (trailing slash).
  if git check-ignore -q "$path" || git check-ignore -q "$path/"; then
    continue
  fi
  echo "  ✗ build output NOT gitignored: $path" >&2
  fail=1
done < "$MAP"

if [ "$fail" -ne 0 ]; then
  {
    echo ""
    echo "Add the path(s) above to the appropriate .gitignore (AE-0171). A documented"
    echo "build/coverage output must be ignored — and untracked (git rm --cached) if it"
    echo "was committed — so artifacts never pollute eslint/QA."
  } >&2
  exit 1
fi
echo "Build-output gitignore pre-flight OK ($checked outputs checked)."
