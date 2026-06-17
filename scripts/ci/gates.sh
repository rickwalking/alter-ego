#!/usr/bin/env bash
# =============================================================================
# gates.sh — single source of truth for every quality gate.
#
# Both CI (.github/workflows/*-quality-gates.yml) and the /qa-agent skill invoke
# THIS script. A gate is defined exactly once here, so the local QA verdict and
# the PR verdict cannot drift (the AE QA-guardian fix). Adding a gate to CI means
# adding it here; there is no second definition to keep in sync.
#
# Usage:
#   scripts/ci/gates.sh backend                 # run all backend gates
#   scripts/ci/gates.sh frontend                # run all frontend gates
#   scripts/ci/gates.sh all                     # backend + frontend
#   scripts/ci/gates.sh backend:mutation        # run a single gate by name
#   scripts/ci/gates.sh backend --changed-only  # fast local subset (no DB, no slow)
#
# Per-gate exit status (also reflected in the JSON summary line):
#   0   PASS      — gate ran and succeeded
#   1   FAIL      — gate ran and failed
#   77  SKIPPED   — gate could NOT run here (missing service / not applicable).
#                   SKIPPED is INCONCLUSIVE — it is NEVER PASS. The QA agent must
#                   downgrade its verdict for any material skipped gate.
#
# Group invocation exits 1 if ANY gate FAILED. SKIPPED alone does not fail the
# group exit, but every skip is recorded in the GATES_JSON summary so callers
# can treat it as inconclusive.
#
# Env:
#   GATES_REQUIRE_ALL=1   Treat SKIPPED as FAIL (set by CI — services must exist).
#   GATES_BASE_REF=ref    Diff base for changed-file gates (default: origin/main).
#   DATABASE_URL=...      Presence enables the Postgres-dependent gates locally.
# =============================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$REPO_ROOT/scripts/ci"
BASE_REF="${GATES_BASE_REF:-origin/main}"

readonly EXIT_PASS=0
readonly EXIT_FAIL=1
readonly EXIT_SKIP=77

# Gates skipped by --changed-only: need a service (DB) or are slow / whole-repo.
CHANGED_ONLY_SKIP=" test diff-cover migrations mutation "

# -----------------------------------------------------------------------------
# Result accumulation
# -----------------------------------------------------------------------------
RESULT_NAMES=()
RESULT_STATUS=()

record() { RESULT_NAMES+=("$1"); RESULT_STATUS+=("$2"); }

postgres_available() {
  # A DATABASE_URL (CI service or local override) is the contract for DB gates.
  [[ -n "${DATABASE_URL:-}" ]]
}

# Run one gate function, capture status, normalise SKIPPED under GATES_REQUIRE_ALL.
run_gate() {
  local name="$1" fn="$2"
  echo "::group::gate ${name}" 2>/dev/null || echo "----- gate ${name} -----"
  ( "$fn" )
  local code=$?
  echo "::endgroup::" 2>/dev/null || true

  local status
  case "$code" in
    "$EXIT_PASS") status="PASS" ;;
    "$EXIT_SKIP")
      if [[ "${GATES_REQUIRE_ALL:-0}" == "1" ]]; then
        status="FAIL"
        echo "ERROR: gate '${name}' was SKIPPED but GATES_REQUIRE_ALL=1 (CI requires every gate to run)." >&2
      else
        status="SKIP"
      fi
      ;;
    *) status="FAIL" ;;
  esac
  echo ">>> ${name}: ${status}"
  record "$name" "$status"
}

# =============================================================================
# Backend gates — each command is byte-faithful to backend-quality-gates.yml
# =============================================================================
gate_backend_format()   { cd "$REPO_ROOT/backend" && uv run ruff format --check src/; }
gate_backend_lint()     { cd "$REPO_ROOT/backend" && uv run ruff check src/; }

gate_backend_lint_diff() {
  cd "$REPO_ROOT"
  git fetch origin main --depth=1 2>/dev/null || {
    echo "origin/main unavailable — skipping ruff diff check."; return "$EXIT_SKIP"; }
  mapfile -t CHANGED < <(git diff --name-only "${BASE_REF}"...HEAD -- 'backend/**/*.py' 2>/dev/null | sed 's|^backend/||')
  ((${#CHANGED[@]} == 0)) && { echo "No changed Python files."; return "$EXIT_PASS"; }
  cd "$REPO_ROOT/backend" && uv run ruff check --diff "${CHANGED[@]}"
}

gate_backend_blanket_ignore() {
  cd "$REPO_ROOT/backend"
  if grep -q 'src/rag_backend/\*\*' pyproject.toml; then
    echo "ERROR: Blanket ignore 'src/rag_backend/**' found in pyproject.toml" >&2
    echo "Per-file-ignores must target specific files, not whole directories." >&2
    return "$EXIT_FAIL"
  fi
  echo "OK: no blanket ignore."
}

gate_backend_strict_diff() { bash "$SCRIPT_DIR/ruff-strict-changed.sh"; }
gate_backend_type()        { cd "$REPO_ROOT/backend/src" && uv run mypy rag_backend/ --explicit-package-bases; }
gate_backend_imports()     { cd "$REPO_ROOT/backend" && uv run lint-imports; }
gate_backend_arch_ratchet() { cd "$REPO_ROOT" && python3 scripts/metrics/import_baseline.py --check; }
gate_backend_docstrings()  { cd "$REPO_ROOT/backend" && uv run interrogate src/ --verbose; }
gate_backend_dead_code()   { cd "$REPO_ROOT/backend" && uv run vulture src/ vulture_whitelist.py --min-confidence 80; }
# Bandit is ADVISORY in CI (report artifact, `|| true`). Mirror that here so the
# QA verdict matches CI — the security subagent does the deep analysis.
gate_backend_bandit()      { cd "$REPO_ROOT/backend" && { uv run bandit -r src/ || echo "ADVISORY: bandit findings above (non-blocking, mirrors CI)."; }; }
gate_backend_pip_audit() {
  cd "$REPO_ROOT/backend"
  uv run pip-audit --desc --ignore-vuln PYSEC-2022-42969 --ignore-vuln PYSEC-2026-196
}

gate_backend_integrity()  { bash "$SCRIPT_DIR/check-integrity.sh" backend; }

gate_backend_test() {
  postgres_available || { echo "DATABASE_URL not set — Postgres-dependent gate cannot run locally."; return "$EXIT_SKIP"; }
  cd "$REPO_ROOT/backend" && uv run pytest --cov=rag_backend --cov-report=xml --cov-report=term
}

gate_backend_diff_cover() {
  postgres_available || { echo "DATABASE_URL not set — diff-cover needs coverage.xml from the test gate."; return "$EXIT_SKIP"; }
  cd "$REPO_ROOT"
  git fetch origin main --depth=1 2>/dev/null || { echo "origin/main unavailable."; return "$EXIT_SKIP"; }
  [[ -f "$REPO_ROOT/backend/coverage.xml" ]] || { echo "coverage.xml absent — run the 'test' gate first."; return "$EXIT_SKIP"; }
  cd "$REPO_ROOT/backend" && uv run diff-cover coverage.xml --compare-branch="${BASE_REF}" --fail-under=75
}

gate_backend_migrations() {
  postgres_available || { echo "DATABASE_URL not set — migration gate cannot run locally."; return "$EXIT_SKIP"; }
  cd "$REPO_ROOT/backend"
  uv run alembic upgrade head || return "$EXIT_FAIL"
  local before new
  before=$(ls alembic/versions/*.py 2>/dev/null | sort)
  uv run alembic revision --autogenerate -m _driftcheck >/dev/null || return "$EXIT_FAIL"
  new=$(comm -13 <(printf '%s\n' "$before") <(ls alembic/versions/*.py | sort))
  if [[ -z "$new" ]]; then echo "ERROR: drift check could not generate a revision" >&2; return "$EXIT_FAIL"; fi
  if grep -Eq '^\s*op\.' "$new"; then
    echo "ERROR: Schema drift — models differ from the alembic baseline (AE-0086)." >&2
    grep -E '^\s*op\.' "$new" || true
    rm -f "$new"; return "$EXIT_FAIL"
  fi
  rm -f "$new"
  uv run alembic downgrade base
}

gate_backend_mutation() { bash "$SCRIPT_DIR/mutation-score-gate.sh" 75; }

# =============================================================================
# Frontend gates — byte-faithful to frontend-quality-gates.yml
# =============================================================================
gate_frontend_lint()            { cd "$REPO_ROOT/frontend" && npm run lint; }
gate_frontend_lint_changed()    { cd "$REPO_ROOT/frontend" && npm run lint:changed; }
# Component-type-location ratchet (AE-0144). Also runs inside `npm run lint`;
# registered standalone so CI and /qa-agent can invoke it directly and report it
# as its own gate (mirrors how boundaries/url/circular live under lint).
gate_frontend_component_types() { cd "$REPO_ROOT/frontend" && npm run lint:component-types; }
gate_frontend_typecheck()       { cd "$REPO_ROOT/frontend" && npm run typecheck; }
# Source-scoped copy-paste detection (AE-0149). Also runs inside `npm run lint`;
# registered standalone so CI and /qa-agent can invoke it directly. Threshold
# lives in frontend/.jscpd.json and may only ratchet DOWN (raising it is flagged
# by check-integrity.sh). Test/spec/story files are excluded by design — egregious
# test duplication is advisory only (AE-0151, gate_frontend_duplication_tests).
gate_frontend_duplication()     { cd "$REPO_ROOT/frontend" && npm run lint:dup; }
# Advisory in CI (continue-on-error); reports test-file duplication, never blocks.
gate_frontend_duplication_tests() { cd "$REPO_ROOT/frontend" && { npm run lint:dup:tests || echo "ADVISORY: jscpd test-duplication findings above (non-blocking, mirrors CI)."; }; }
gate_frontend_legacy_guard()    { cd "$REPO_ROOT/frontend" && npm run check:legacy; }
gate_frontend_legacy_inventory() { cd "$REPO_ROOT/frontend" && npm run check:legacy-inventory; }
gate_frontend_test()            { cd "$REPO_ROOT/frontend" && npm run test -- --run; }
gate_frontend_security()        { cd "$REPO_ROOT/frontend" && npm audit --audit-level=high; }
gate_frontend_format()          { cd "$REPO_ROOT/frontend" && npx prettier --check "src/**/*.{ts,tsx,json,css,md}"; }
gate_frontend_integrity()       { bash "$SCRIPT_DIR/check-integrity.sh" frontend; }
# Advisory in CI (continue-on-error); reported but never blocks.
gate_frontend_mutation()        { cd "$REPO_ROOT/frontend" && { npm run test:mutate || echo "ADVISORY: Stryker findings above (non-blocking, mirrors CI)."; }; }
# OpenAPI<->Zod schema-drift (AE-0141). BLOCKING (AE-0157): drift reconciled to
# 0; the npm script runs with --strict so any new drift exits non-zero.
gate_frontend_schema_drift()    { cd "$REPO_ROOT/frontend" && npm run check:schema-drift; }

# =============================================================================
# Gate registries (ordered). Name -> function.
# =============================================================================
BACKEND_GATES=(
  format:gate_backend_format
  lint:gate_backend_lint
  lint-diff:gate_backend_lint_diff
  blanket-ignore:gate_backend_blanket_ignore
  strict-diff:gate_backend_strict_diff
  type:gate_backend_type
  imports:gate_backend_imports
  arch-ratchet:gate_backend_arch_ratchet
  docstrings:gate_backend_docstrings
  dead-code:gate_backend_dead_code
  bandit:gate_backend_bandit
  pip-audit:gate_backend_pip_audit
  integrity:gate_backend_integrity
  test:gate_backend_test
  diff-cover:gate_backend_diff_cover
  migrations:gate_backend_migrations
  mutation:gate_backend_mutation
)

FRONTEND_GATES=(
  lint:gate_frontend_lint
  lint-changed:gate_frontend_lint_changed
  component-types:gate_frontend_component_types
  duplication:gate_frontend_duplication
  typecheck:gate_frontend_typecheck
  legacy-guard:gate_frontend_legacy_guard
  legacy-inventory:gate_frontend_legacy_inventory
  format:gate_frontend_format
  security:gate_frontend_security
  integrity:gate_frontend_integrity
  test:gate_frontend_test
  schema-drift:gate_frontend_schema_drift
  duplication-tests:gate_frontend_duplication_tests
  mutation:gate_frontend_mutation
)

lookup_fn() {
  local scope="$1" gate="$2" entry
  local -n registry="$([[ "$scope" == backend ]] && echo BACKEND_GATES || echo FRONTEND_GATES)"
  for entry in "${registry[@]}"; do
    [[ "${entry%%:*}" == "$gate" ]] && { echo "${entry#*:}"; return 0; }
  done
  return 1
}

run_scope() {
  local scope="$1" changed_only="$2" entry name fn
  local -n registry="$([[ "$scope" == backend ]] && echo BACKEND_GATES || echo FRONTEND_GATES)"
  for entry in "${registry[@]}"; do
    name="${entry%%:*}"; fn="${entry#*:}"
    if [[ "$changed_only" == "1" && "$CHANGED_ONLY_SKIP" == *" $name "* ]]; then
      echo ">>> ${scope}:${name}: SKIP (--changed-only)"; record "${scope}:${name}" "SKIP"; continue
    fi
    run_gate "${scope}:${name}" "$fn"
  done
}

print_summary() {
  local i n_pass=0 n_fail=0 n_skip=0 json="" sep=""
  echo
  echo "================= GATE SUMMARY ================="
  for i in "${!RESULT_NAMES[@]}"; do
    printf '  %-28s %s\n' "${RESULT_NAMES[$i]}" "${RESULT_STATUS[$i]}"
    case "${RESULT_STATUS[$i]}" in
      PASS) ((n_pass++)) ;; FAIL) ((n_fail++)) ;; SKIP) ((n_skip++)) ;;
    esac
    json="${json}${sep}{\"gate\":\"${RESULT_NAMES[$i]}\",\"status\":\"${RESULT_STATUS[$i]}\"}"; sep=","
  done
  echo "-----------------------------------------------"
  echo "  PASS=${n_pass}  FAIL=${n_fail}  SKIP=${n_skip}"
  echo "==============================================="
  # Machine-readable line for the QA agent to parse.
  echo "GATES_JSON: {\"pass\":${n_pass},\"fail\":${n_fail},\"skip\":${n_skip},\"results\":[${json}]}"
  return "$n_fail"
}

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------
TARGET="${1:-}"
CHANGED_ONLY=0
for arg in "${@:2}"; do
  [[ "$arg" == "--changed-only" ]] && CHANGED_ONLY=1
done

[[ -z "$TARGET" ]] && { echo "Usage: gates.sh <backend|frontend|all|scope:gate> [--changed-only]" >&2; exit 2; }

case "$TARGET" in
  all)
    run_scope backend "$CHANGED_ONLY"
    run_scope frontend "$CHANGED_ONLY"
    ;;
  backend|frontend)
    run_scope "$TARGET" "$CHANGED_ONLY"
    ;;
  *:*)
    scope="${TARGET%%:*}"; gate="${TARGET#*:}"
    [[ "$scope" == backend || "$scope" == frontend ]] || { echo "Unknown scope: $scope" >&2; exit 2; }
    fn="$(lookup_fn "$scope" "$gate")" || { echo "Unknown gate: $TARGET" >&2; exit 2; }
    run_gate "$TARGET" "$fn"
    ;;
  *)
    echo "Unknown target: $TARGET" >&2; exit 2 ;;
esac

print_summary
exit $?
