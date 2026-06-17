#!/usr/bin/env bash
# =============================================================================
# check-integrity.sh — diff-scoped anti-gaming ratchet (the QA-guardian sensor).
#
# Goodhart's-law defense: detects attempts to make CI green by gaming the gates
# rather than meeting them. It inspects ONLY what the diff ADDS vs the base ref,
# so pre-existing debt is reported but never blocks; a developer can only be
# bounced for NET-NEW gaming they introduced.
#
# Categories & severity:
#   BLOCKER (exit 1)  net-new suppressions (# noqa / # type: ignore / # nosec /
#                     # pragma: no cover / eslint-disable / @ts-ignore / ...),
#                     net-new skipped/weakened tests, threshold DECREASES, and
#                     net-new prohibited DDD imports.
#   WARN    (exit 0)  new threshold/ignore additions and edits to the gate
#                     apparatus itself (workflows, scripts/ci, import_baseline
#                     baseline, .importlinter, eslint/tsconfig/stryker). Surfaced
#                     for human/QA review with ticket context.
#
# Sanctioned, auditable escape hatch: append `integrity-ok: <reason>` to the SAME
# added line (`# integrity-ok:` / `// integrity-ok:`) to downgrade a BLOCKER to a
# WARN. QA reviews every such marker — it is a visible decision, not a silent one.
#
# Usage:   check-integrity.sh [backend|frontend|all]   (default: all)
# Env:     GATES_BASE_REF=ref   diff base (default: origin/main)
# =============================================================================
set -uo pipefail

SCOPE="${1:-all}"
BASE_REF="${GATES_BASE_REF:-origin/main}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
git fetch origin main --depth=1 2>/dev/null || true

case "$SCOPE" in
  backend)  PATHSPEC=(backend/ .github/workflows/ scripts/) ;;
  frontend) PATHSPEC=(frontend/) ;;
  all)      PATHSPEC=(.) ;;
  *) echo "Usage: check-integrity.sh [backend|frontend|all]" >&2; exit 2 ;;
esac

# AE-0171 pre-flight: every documented build/coverage output must be gitignored,
# so a stray artifact never breaks eslint/QA. Fails integrity if one is missing.
if ! bash "$(dirname "${BASH_SOURCE[0]}")/check-build-output-ignored.sh"; then
  echo "FAIL: a documented build output is not gitignored (AE-0171)." >&2
  exit 1
fi

DIFF_FILE="$(mktemp)"; NAMES_FILE="$(mktemp)"
trap 'rm -f "$DIFF_FILE" "$NAMES_FILE"' EXIT
git diff "${BASE_REF}...HEAD" -U0 -- "${PATHSPEC[@]}" 2>/dev/null > "$DIFF_FILE"
git diff --name-only "${BASE_REF}...HEAD" -- "${PATHSPEC[@]}" 2>/dev/null > "$NAMES_FILE"

DIFF_FILE="$DIFF_FILE" NAMES_FILE="$NAMES_FILE" BASE_REF="$BASE_REF" python3 - <<'PY'
import os, re, sys

with open(os.environ["DIFF_FILE"], encoding="utf-8", errors="replace") as fh:
    diff = fh.read()
with open(os.environ["NAMES_FILE"], encoding="utf-8", errors="replace") as fh:
    names = [n for n in fh.read().splitlines() if n.strip()]

blockers, warns = [], []
ESC = re.compile(r"integrity-ok:")

def add(sev_list, file, line, cat, snippet, line_no=None):
    loc = f"{file}:{line_no}" if line_no else file
    sev_list.append((loc, cat, snippet.strip()[:160]))

# ----- parse unified diff into added / removed lines per file ---------------
added, removed = [], []   # (file, lineno|None, text)
cur, newno = None, 0
for raw in diff.splitlines():
    if raw.startswith("+++ b/"):
        cur = raw[6:]; continue
    if raw.startswith("@@"):
        m = re.search(r"\+(\d+)", raw)
        newno = int(m.group(1)) if m else 0
        continue
    if cur is None:
        continue
    if raw.startswith("+") and not raw.startswith("+++"):
        added.append((cur, newno, raw[1:])); newno += 1
    elif raw.startswith("-") and not raw.startswith("---"):
        removed.append((cur, None, raw[1:]))
    elif not raw.startswith("\\"):
        newno += 1

# ----- 1. suppression tokens ------------------------------------------------
SUPPRESS = [
    (r"#\s*type:\s*ignore", "suppression:type-ignore"),
    (r"#\s*mypy:\s*ignore", "suppression:mypy-ignore"),
    (r"#\s*noqa", "suppression:noqa"),
    (r"#\s*ruff:\s*noqa", "suppression:ruff-noqa"),
    (r"#\s*nosec", "suppression:nosec"),
    (r"#\s*pragma:\s*no\s*cover", "suppression:no-cover"),
    (r"eslint-disable", "suppression:eslint-disable"),
    (r"@ts-ignore", "suppression:ts-ignore"),
    (r"@ts-expect-error", "suppression:ts-expect-error"),
    (r"@ts-nocheck", "suppression:ts-nocheck"),
    (r"prettier-ignore", "suppression:prettier-ignore"),
]
# ----- 2. skipped / weakened tests -----------------------------------------
SKIPS = [
    (r"@pytest\.mark\.skip", "test-skip:pytest-skip"),
    (r"@pytest\.mark\.xfail", "test-skip:pytest-xfail"),
    (r"\bpytest\.skip\(", "test-skip:pytest-skip-call"),
    (r"^\s*assert\s+True\s*$", "test-weak:assert-true"),
    (r"\bdescribe\.skip\b", "test-skip:describe-skip"),
    (r"\bit\.skip\b", "test-skip:it-skip"),
    (r"\.only\(", "test-focus:only"),
    (r"\bxit\(", "test-skip:xit"),
    (r"\bxdescribe\(", "test-skip:xdescribe"),
]

def is_testish(path):
    return "/tests/" in path or path.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")) or "/test_" in path or path.split("/")[-1].startswith("test_")

# Suppression / skip tokens only matter in SOURCE files. Docs, the guardian
# scanner itself, SKILL/config, markdown and YAML legitimately mention these
# strings — scanning them would self-flag.
CODE_EXT = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
def is_code(path):
    return path.endswith(CODE_EXT)

for f, ln, text in added:
    if not is_code(f):
        continue
    escaped = bool(ESC.search(text))
    for rx, cat in SUPPRESS:
        if re.search(rx, text):
            add(warns if escaped else blockers, f, ln, cat, text, ln)
    for rx, cat in SKIPS:
        if re.search(rx, text):
            # `.only(` only meaningful in test files; assert-True only in tests
            if cat in ("test-focus:only",) and not is_testish(f):
                continue
            add(warns if escaped else blockers, f, ln, cat, text, ln)

# ----- 3. config / threshold loosening -------------------------------------
CONFIG_HINT = ("pyproject.toml", ".coveragerc", "setup.cfg", "stryker.conf",
               "tsconfig", "eslint.config", ".importlinter", ".jscpd",
               "dead-code-baseline")
def is_config(p): return any(h in p for h in CONFIG_HINT)

# Direction-aware threshold gaming, detected by pairing removed/added lines.
#   lower-is-gaming: coverage / mutation / diff-cover minimums.
#   higher-is-gaming: complexity & arg budgets and the architecture baseline.
LOWER_IS_GAMING = [r"fail[_-]under", r"--fail-under"]
HIGHER_IS_GAMING = [
    r"max-complexity", r"max-args", r"max-branches", r"max-returns",
    r"max-locals", r"max-nested-blocks", r"BASELINE_\w+",
    # jscpd duplication ceiling (AE-0149): higher % = more duplication tolerated.
    # The threshold may only ratchet DOWN; raising it re-permits duplication.
    r'"threshold"',
    # Dead-export baseline count (AE-0152): higher = more grandfathered dead
    # code. The baseline is down-only; raising the count re-permits dead exports.
    r'"count"',
]
# Net-new rule disabling — always a BLOCKER (escape hatch downgrades to WARN).
LOOSEN_KEYS = [
    (r"per-file-ignores", "loosen:per-file-ignores"),
    (r"ignore_errors\s*=\s*true", "loosen:mypy-ignore-errors"),
    (r"disable_error_code", "loosen:mypy-disable-error-code"),
    (r"paths_to_mutate", "loosen:mutmut-paths"),
]
def num(s):
    m = re.search(r"(\d+(?:\.\d+)?)", s); return float(m.group(1)) if m else None

def paired_threshold(keys, gaming_is_lower):
    for key in keys:
        rx = re.compile(key)
        rem = [(f, t) for f, _, t in removed if rx.search(t) and (is_config(f) or f.endswith("import_baseline.py"))]
        addd = [(f, ln, t) for f, ln, t in added if rx.search(t) and (is_config(f) or f.endswith("import_baseline.py"))]
        for f, t in rem:
            for f2, ln2, t2 in addd:
                if f2 != f:
                    continue
                a, b = num(t), num(t2)
                if a is None or b is None:
                    continue
                gamed = (b < a) if gaming_is_lower else (b > a)
                if gamed:
                    add(blockers, f2, ln2, "threshold-loosened",
                        f"{t.strip()}  ->  {t2.strip()}", ln2)

paired_threshold(LOWER_IS_GAMING, gaming_is_lower=True)
paired_threshold(HIGHER_IS_GAMING, gaming_is_lower=False)

for f, ln, text in added:
    if not is_config(f):
        continue
    escaped = bool(ESC.search(text))
    for rx, cat in LOOSEN_KEYS:
        if re.search(rx, text):
            add(warns if escaped else blockers, f, ln, cat, text, ln)
    # New coverage omit entries are a softer signal — surface for review.
    if re.search(r"^\s*omit\s*=", text):
        add(warns, f, ln, "loosen:coverage-omit", text, ln)

# ----- 4. apparatus tampering (WARN — needs ticket justification) -----------
APPARATUS = [
    r"\.github/workflows/.*quality-gates\.yml$",
    r"\.github/workflows/mutation-weekly\.yml$",
    r"^scripts/ci/",
    r"^scripts/metrics/import_baseline\.py$",
    r"\.importlinter$",
    r"eslint\.config", r"tsconfig.*\.json$", r"stryker\.conf",
]
for f in names:
    for rx in APPARATUS:
        if re.search(rx, f):
            add(warns, f, "-", "apparatus-edit", "gate definition modified — QA must confirm ticket justifies it")
            break
# Raising a BASELINE_ ceiling re-permits violations — caught by the
# direction-aware HIGHER_IS_GAMING pass above (paired +/- numeric increase).

# ----- 5. prohibited DDD imports (net-new in backend src) -------------------
def layer(p):
    m = re.search(r"backend/src/rag_backend/(\w+)/", p)
    return m.group(1) if m else None

FORBIDDEN = {  # importer-layer -> set of forbidden target packages
    "domain":      ("application", "infrastructure", "api", "agents"),
    "application": ("infrastructure", "agents", "api"),
    "agents":      ("application", "api"),
    "infrastructure": ("api",),
}
imp_rx = re.compile(r"^\s*(?:from|import)\s+rag_backend\.(\w+)")
for f, ln, text in added:
    lyr = layer(f)
    if not lyr:
        continue
    m = imp_rx.match(text)
    if m and m.group(1) in FORBIDDEN.get(lyr, ()):
        escaped = bool(ESC.search(text))
        add(warns if escaped else blockers, f, ln, f"ddd-import:{lyr}->{m.group(1)}", text, ln)
    if "get_container(" in text and not re.search(r"/(bootstrap|api/dependencies)/", f):
        add(blockers, f, ln, "ddd:service-locator", text, ln)
    if ".commit(" in text and "/infrastructure/database/" in f:
        add(blockers, f, ln, "ddd:adapter-commit", text, ln)

# ----- report ---------------------------------------------------------------
def render(title, items):
    print(f"\n=== {title} ({len(items)}) ===")
    for loc, cat, snip in items:
        print(f"  [{cat}] {loc}")
        if snip and snip != "-":
            print(f"      {snip}")

print(f"Integrity scan (diff vs {os.environ.get('BASE_REF','origin/main')}) — net-new only.")
render("🔴 BLOCKERS (net-new gaming — bounce to developer)", blockers)
render("🟠 WARNINGS (review with ticket context)", warns)

if blockers:
    print(f"\nFAIL: {len(blockers)} net-new integrity blocker(s). "
          "Fix the underlying issue — do not suppress, skip, or loosen the gate.")
    sys.exit(1)
if warns:
    print(f"\nPASS (with {len(warns)} warning(s) for review).")
else:
    print("\nPASS: no net-new gaming detected.")
sys.exit(0)
PY
