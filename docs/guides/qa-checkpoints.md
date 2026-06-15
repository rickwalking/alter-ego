# QA Checkpoints Reference

> Comprehensive reference for all QA validation checkpoints used by the QA Agent skill.
> Covers OWASP Top 10:2025, code quality standards, mutation testing thresholds,
> acceptance criteria validation, and orphan/unfinished code detection.

## Table of Contents

1. [Security Checkpoints (OWASP Top 10:2025)](#1-security-checkpoints-owasp-top-102025)
2. [Code Quality Checkpoints](#2-code-quality-checkpoints)
3. [Mutation Testing Thresholds](#3-mutation-testing-thresholds)
4. [Acceptance Criteria Validation](#4-acceptance-criteria-validation)
5. [Orphan & Unfinished Code Detection](#5-orphan--unfinished-code-detection)
6. [Dependency Security](#6-dependency-security)
7. [CI/CD Quality Gates](#7-cicd-quality-gates)
8. [Tool Reference](#8-tool-reference)
9. [False Positive Management](#9-false-positive-management)

---

## 1. Security Checkpoints (OWASP Top 10:2025)

### A01:2025 - Broken Access Control

| Checkpoint | How to Verify | Tool/Command |
|------------|---------------|--------------|
| Authorization on all protected endpoints | Inspect route handlers for auth middleware/decorators | Manual code inspection |
| Role-based permissions enforced server-side | Check that frontend role checks are mirrored server-side | Manual code inspection |
| No IDOR vulnerabilities | Verify object ownership checks before returning data | Manual + semgrep |
| CORS configured restrictively | Check CORSMiddleware settings | ruff + manual |
| Rate limiting on auth endpoints | Look for rate limiter middleware | Manual inspection |

**References:**
- OWASP: https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/
- CWE-284: Improper Access Control
- CWE-639: Authorization Bypass Through User-Controlled Key

### A02:2025 - Security Misconfiguration

| Checkpoint | How to Verify | Tool/Command |
|------------|---------------|--------------|
| Debug mode disabled in production | Check env var usage for debug flags | Manual + grep |
| Default credentials changed | Search for default passwords in config | truffleHog / gitleaks |
| CORS not using wildcard in production | Inspect CORS configuration | Manual |
| HTTP security headers set | Check for X-Frame-Options, CSP, HSTS | Manual |
| Unnecessary features disabled | Check for disabled endpoints/services | Manual |
| Error handling does not leak stack traces | Check exception handlers | Manual |

**References:**
- OWASP: https://owasp.org/Top10/2025/A02_2025-Security_Misconfiguration/
- CWE-16: Configuration

### A03:2025 - Software Supply Chain Failures

| Checkpoint | How to Verify | Tool/Command |
|------------|---------------|--------------|
| No dependencies with known critical vulnerabilities | Run vulnerability scanner | pip audit / npm audit |
| Dependencies within 7-day update window | Check release dates of current versions | pip list --outdated / npm outdated |
| CI/CD pipeline signed/verified | Check workflow configuration | Manual |
| Dependency integrity verified | Check lock files (not just loose versions) | Verify uv.lock / package-lock.json |
| No malicious packages | Run pip audit / npm audit | pip audit / npm audit |

**References:**
- OWASP: https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/
- CWE-1104: Use of Unmaintained Third-Party Components

### A04:2025 - Cryptographic Failures

| Checkpoint | How to Verify | Tool/Command |
|------------|---------------|--------------|
| Passwords hashed with bcrypt/argon2 | Check auth service | Manual + grep for hash functions |
| TLS enforced in production | Check HTTPS configuration | Manual |
| Secrets encrypted at rest | Check secret storage | Manual |
| No weak crypto algorithms (MD5, SHA1, RC4) | Search for weak algorithm usage | ruff S rules + manual |
| Proper key management | Check where keys are stored/rotated | Manual |

**References:**
- OWASP: https://owasp.org/Top10/2025/A04_2025-Cryptographic_Failures/
- CWE-327: Use of a Broken or Risky Cryptographic Algorithm

### A05:2025 - Injection

| Checkpoint | How to Verify | Tool/Command |
|------------|---------------|--------------|
| All SQL queries parameterized | Check for raw SQL string concatenation | ruff S rules + semgrep |
| No eval() / exec() calls | Search for dynamic code execution | grep for eval(, exec( |
| No raw NoSQL queries | Check MongoDB/other DB query construction | Manual |
| Input validation at API boundary | Check Pydantic/Zod schemas | Manual |
| Output encoding for HTML/JS | Check template rendering | Manual |

**References:**
- OWASP: https://owasp.org/Top10/2025/A05_2025-Injection/
- CWE-89: SQL Injection
- CWE-79: Cross-site Scripting (XSS)

### A06:2025 - Insecure Design

| Checkpoint | How to Verify | Tool/Command |
|------------|---------------|--------------|
| Rate limiting on API endpoints | Check for rate limiter middleware | Manual |
| Input validation at boundary | Check schema definitions | Manual |
| Business logic not bypassable | Test edge cases in business logic | Manual review |
| Secure defaults used | Check default values in configs | Manual |

**References:**
- OWASP: https://owasp.org/Top10/2025/A06_2025-Insecure_Design/
- CWE-657: Violation of Secure Design Principles

### A07:2025 - Authentication Failures

| Checkpoint | How to Verify | Tool/Command |
|------------|---------------|--------------|
| Session tokens properly managed | Check token generation, storage, expiry | Manual |
| MFA available (if applicable) | Check auth configuration | Manual |
| Password policies enforced | Check password validation rules | Manual |
| No hardcoded credentials | Search for hardcoded secrets | truffleHog / gitleaks |
| Brute force protection | Check for account lockout | Manual |

**References:**
- OWASP: https://owasp.org/Top10/2025/A07_2025-Authentication_Failures/
- CWE-287: Improper Authentication

### A08:2025 - Software and Data Integrity Failures

| Checkpoint | How to Verify | Tool/Command |
|------------|---------------|--------------|
| CI/CD pipeline integrity | Check for unsigned artifacts | Manual |
| Dependency integrity | Verify checksums in lock files | Manual |
| No unsigned auto-update mechanisms | Check update logic | Manual |

**References:**
- OWASP: https://owasp.org/Top10/2025/A08_2025-Software_or_Data_Integrity_Failures/
- CWE-829: Inclusion of Functionality from Untrusted Control Sphere

### A09:2025 - Security Logging and Monitoring Failures

| Checkpoint | How to Verify | Tool/Command |
|------------|---------------|--------------|
| Security events logged (auth failures, access denials) | Check logging configuration | Manual |
| Logs exclude PII | Check log statements for sensitive data | Manual + grep |
| Logs are monitored/alerted | Check monitoring setup | Manual |
| Audit trail for sensitive operations | Check audit logging | Manual |

**References:**
- OWASP: https://owasp.org/Top10/2025/A09_2025-Security_Logging_and_Alerting_Failures/
- CWE-778: Insufficient Logging

### A10:2025 - Mishandling of Exceptional Conditions

| Checkpoint | How to Verify | Tool/Command |
|------------|---------------|--------------|
| Exceptions caught and handled properly | Check try/except blocks | Manual + ruff |
| Error messages don't leak internals | Check error response format | Manual |
| Graceful degradation on failure | Check fallback behavior | Manual |
| No bare except: clauses | Check for overly broad exception handling | ruff PLE0704 + manual |

**References:**
- OWASP: https://owasp.org/Top10/2025/A10_2025-Mishandling_of_Exceptional_Conditions/
- CWE-248: Uncaught Exception
- CWE-209: Information Exposure Through an Error Message

---

## 2. Code Quality Checkpoints

### Linting (ruff / ESLint)

| Checkpoint | Command | Threshold |
|------------|---------|-----------|
| No lint errors | ruff check src/ (backend) / eslint src/ (frontend) | Zero errors |
| No lint warnings | ruff check --show-fixes src/ | Zero warnings (preferred) |
| No unused imports | ruff check --select F401 src/ | Zero |
| No unused variables | ruff check --select F841 src/ | Zero |
| No commented-out code | ruff check --select ERA001 src/ | Zero |

### Type Checking

| Checkpoint | Command | Threshold |
|------------|---------|-----------|
| mypy strict passes | mypy --strict src/ | Zero errors |
| No explicit Any | disallow_any_explicit = true in mypy config | Zero |
| No bare generics | disallow_any_generics = true in mypy config | Zero |
| All functions have return types | disallow_untyped_defs = true | Zero |
| TypeScript strict passes | tsc --noEmit --strict | Zero errors |

### Complexity

| Checkpoint | Tool | Threshold |
|------------|------|-----------|
| Cyclomatic complexity per function | ruff C90 | Max 10 |
| Module average complexity | xenon | Max A (CC avg less than or equal 5) |
| Max branches per function | ruff PLR0912 | Max 10 |
| Max statements per function | ruff PLR0915 | Max 40 |
| Max nested blocks | ruff | Max 4 |
| Max arguments per function | ruff PLR0913 | Max 3; use Pydantic models for API/service boundary payloads |
| Max return statements | ruff PLR0911 | Max 6 |
| Max locals per function | ruff | Max 15 |

### File and Function Size

| Checkpoint | How to Verify | Threshold |
|------------|---------------|-----------|
| Max lines per file | wc -l on each file | 400 |
| Max lines per function | Manual inspection | 50 |
| Max line length | ruff E501 | 100 (backend) / 80 (frontend) |

### Architecture

| Checkpoint | Tool | Threshold |
|------------|------|-----------|
| Import boundaries respected | import-linter / pytest-archon | Zero violations |
| No circular dependencies | grimp | Zero |
| Layer isolation (domain to infrastructure) | import-linter layers | Zero violations |
| Per-category import-violation ratchet | `import_baseline.py --check` (AE-0082) | No category above committed baseline |
| Architecture health report | `import_baseline.py --summary` (AE-0085) | Per-category counts vs baseline (Step Summary + artifact) |

The modularization ratchet (AE-0078 → AE-0082 → AE-0085) tracks **six**
categories against a single committed baseline
(`.agent/reports/import-violations-baseline.md`): the four import
layer/module-pair categories (`application -> infrastructure`,
`application -> agents`, `agents -> application`, `api -> infrastructure`),
the `get_container()` locator sites, and the adapter `.commit()` sites. Each
count may stay equal or decrease, never rise. See
[Architecture ratchet and baseline-down procedure](#architecture-ratchet-and-baseline-down-procedure).

### Documentation

| Checkpoint | Tool | Threshold |
|------------|------|-----------|
| Public functions documented | ruff D (D100-D107) | Google convention |
| Docstrings match signatures | Manual / pydoclint | Match |

### Naming Conventions

| Checkpoint | Tool | Threshold |
|------------|------|-----------|
| No magic strings | Manual + ruff | All strings in constants |
| Python snake_case | ruff N | Pass |
| TypeScript camelCase | eslint naming rules | Pass |
| Constants UPPER_SNAKE_CASE | Manual | Pass |

---

## 3. Mutation Testing Thresholds

> **CI gate (blocking):** the backend `mutation` gate fails the PR below an
> **aggregate 75%** score (`scripts/ci/mutation-score-gate.sh`, run via
> `gates.sh backend:mutation`). The per-module figures below are ADR-005 design
> *targets* for prioritizing where to strengthen tests — they are not separate
> CI thresholds. QA must use **75%** as the pass/fail line, never 70%.

### Backend (mutmut)

| Module Type | Break (Fail) | Low (Warn) | High (Target) |
|-------------|-------------|-------------|---------------|
| Business Logic | 50% | 70% | 80% |
| API Routes | 40% | 60% | 75% |
| Data Access / Repositories | 40% | 60% | 75% |
| Services / Use Cases | 50% | 70% | 80% |

### Frontend (StrykerJS)

| Module Type | Break (Fail) | Low (Warn) | High (Target) |
|-------------|-------------|-------------|---------------|
| Business Logic (hooks, services) | 50% | 70% | 80% |
| API Routes / Server Actions | 40% | 60% | 75% |
| UI Components | 30% | 50% | 65% |
| Utility Functions | 50% | 70% | 80% |

### mutmut Configuration

```toml
[tool.mutmut]
paths_to_exclude = [
    "tests/",
    "migrations/",
    "**/constants.py",
    "**/schemas.py",
]
backup = false
runner = "pytest"
```

### StrykerJS Configuration

```json
{
  "mutate": ["src/**/*.{ts,tsx}", "!src/**/*.test.{ts,tsx}", "!src/**/*.spec.{ts,tsx}"],
  "testRunner": "vitest",
  "reporters": ["html", "progress", "json"],
  "thresholds": {
    "high": 80,
    "low": 50,
    "break": 30
  },
  "mutator": {
    "excludedMutations": ["StringLiteral", "ObjectLiteral"]
  }
}
```

**ADR Reference:** ADR-005: Adopt Mutation Testing

---

## 4. Acceptance Criteria Validation

### Process

1. **Extract criteria** from the plan/spec file
2. **Map each criterion** to test(s) by searching for Gherkin scenarios or test function names
3. **Run specific tests** for each criterion
4. **Verify implementation** satisfies the criterion (not just tests passing)
5. **Report** per-criterion status

### Checklist

| Checkpoint | Method |
|------------|--------|
| Each criterion has at least one test | Search for Gherkin scenario or test matching criterion description |
| Test covers happy path | Verify the primary success case is tested |
| Test covers edge cases | Verify boundary conditions are tested |
| Test covers failure modes | Verify error cases are tested |
| Test actually passes | Run the specific test(s) |
| Implementation satisfies criterion | Manual inspection of code behavior |
| No scope creep | Verify no behavior exists that is not in the criteria |

### Gherkin Mapping Convention

```python
# Feature: Document Management
# Scenario: Create document with valid data
#   Given a valid document payload
#   When POST /api/documents
#   Then returns 201 with created document
async def test_create_document_valid(self, client):
    ...
```

---

## 5. Orphan and Unfinished Code Detection

### Dead Code

| Checkpoint | Tool/Command | Threshold |
|------------|--------------|-----------|
| Unused functions/classes | dead / vulture | Zero in production code |
| Unused imports | ruff F401 | Zero |
| Unused variables | ruff F841 | Zero |
| Commented-out code blocks | ruff ERA001 | Zero |
| Unused route handlers | Manual inspection | Flag for review |
| Unused event listeners | Manual inspection | Flag for review |

### Unfinished Work

| Checkpoint | Tool/Command | Threshold |
|------------|--------------|-----------|
| TODO markers | grep -r TODO src/ | Flag files with 5+ |
| FIXME markers | grep -r FIXME src/ | Flag files with 3+ |
| HACK markers | grep -r HACK src/ | Flag any |
| XXX markers | grep -r XXX src/ | Flag any |
| Stub functions | Search for pass, NotImplementedError | Flag any in production code |
| Empty catch blocks | ruff + manual | Zero |
| Placeholder values | Search for TODO, placeholder, lorem | Flag any |

### Orphaned Files

| Checkpoint | Method |
|------------|--------|
| Files not imported by any other file | Build import graph, find islands |
| Exported functions never called | Cross-reference exports vs. imports |
| Unused CSS classes | PurgeCSS or manual |
| Unused dependencies | pip list / npm ls vs. actual imports |

---

## 6. Dependency Security

### Vulnerability Scanning

| Checkpoint | Command | Threshold |
|------------|---------|-----------|
| Python vulnerabilities | pip audit | Zero critical/high |
| npm vulnerabilities | npm audit | Zero critical/high |
| Outdated packages | pip list --outdated / npm outdated | Flag >7 days behind |

### 7-Day Update Window Policy

Dependencies should be updated within **7 calendar days** of a new release if:
- The release contains a security fix (CVE)
- The release is a patch version (semver)
- The release is for a direct dependency with a critical/high severity advisory

Exceptions require documented justification in an ADR or docs/decisions/.

### Tools

| Tool | Purpose | Installation |
|------|---------|--------------|
| pip-audit | Python vulnerability scanner | pip install pip-audit |
| npm audit | Node.js vulnerability scanner | Built into npm |
| safety | Python vulnerability scanner (alternative) | pip install safety |
| dependabot | GitHub-native dependency updates | Built into GitHub |
| renovate | Cross-platform dependency updater | GitHub app |

---

## 7. CI/CD Quality Gates

Every gate below is defined **once**, in `scripts/ci/gates.sh` — the single
source of truth. Both CI and the `/qa-agent` skill invoke that script, so a green
local QA run means a green CI run (they cannot drift). `/qa-agent` runs
`gates.sh` in **Phase 0** and only adds judgment-based dimensions (acceptance
criteria, deep security, architecture, integrity) on top.

```bash
# Reproduce CI locally (the QA agent does this automatically in Phase 0):
bash scripts/ci/gates.sh backend            # all backend gates
bash scripts/ci/gates.sh frontend           # all frontend gates
bash scripts/ci/gates.sh backend:mutation   # one gate by name
bash scripts/ci/gates.sh backend --changed-only   # fast subset (no DB / no slow)
```

Gates needing Postgres (`test`, `diff-cover`, `migrations`) or that are slow
(`mutation`) report **SKIPPED** when they can't run locally — SKIPPED is
**INCONCLUSIVE, never PASS**. Set `DATABASE_URL` to run the DB-dependent gates.

See [CI Quality Gates Guide](./ci-quality-gates.md) for workflow names, branch protection, and rollout policy.

### CI vs Full QA Agent

| Dimension | CI (blocking) | CI (advisory) | Full `/qa-agent` only |
|-----------|---------------|---------------|------------------------|
| Lint & format | ruff, eslint | — | — |
| Lint (changed files) | ruff `--diff` on changed files (backend), eslint changed | — | — |
| Types | mypy, tsc | — | — |
| Tests & coverage | pytest, vitest, diff-cover ≥75% | — | — |
| Architecture | import-linter | — | Scope / ADR compliance |
| Security | bandit, pip-audit, npm audit (high) | — | IDOR, authz logic |
| Dead code | vulture | — | Orphan routes, TODO sweep |
| Complexity (new code) | Strict Diff (PLR0913/C901/PLR0912/PLR0911/PLR0914/PLR1702), eslint changed | — | — |
| Mutation testing | mutmut ≥75% (backend) | Stryker (frontend) | Deep mutation analysis |
| Integrity / anti-gaming | `check-integrity.sh` (net-new suppressions, skipped tests, loosened thresholds, prohibited imports) | apparatus-edit / coverage-omit warnings | Escape-hatch audit, coverage-gaming review |
| Acceptance criteria | — | — | Plan/spec mapping |

### Backend Quality Gates (`Backend Quality Gates` workflow)

| Job | Tool | Enforcement |
|-----|------|-------------|
| backend / Lint & Format | ruff check + format | CI failure + reviewdog inline (PR) |
| backend / Lint & Format | ruff diff check (changed files only) | **CI failure (blocking — AE-0049)** — fails if changed `.py` files contain ruff violations |
| backend / Lint & Format | Blanket ignore guard (`grep` on `pyproject.toml`) | CI failure — blocks `"src/rag_backend/**"` in per-file-ignores |
| backend / Strict Diff | ruff `--select PLR0913,C901,PLR0912,PLR0911,PLR0914,PLR1702` on changed lines | **CI failure (blocking)** — thresholds below |
| backend / Type Check | mypy | CI failure |
| backend / Architecture | import-linter | CI failure |
| backend / Architecture | `import_baseline.py --check` (AE-0082 ratchet) | **CI failure (blocking)** if any of the six categories rises above the committed baseline |
| backend / Architecture | `import_baseline.py --summary` (AE-0085 report) | Non-blocking — writes the per-category report to the GitHub Step Summary and uploads it as the `architecture-report` artifact |
| backend / Docstrings | interrogate ≥80% | CI failure |
| backend / Security | bandit + pip-audit | CI failure |
| backend / Test & Coverage | pytest + diff-cover ≥75% | CI failure (blocking) |
| backend / Migrations (fresh DB) | `alembic upgrade head` + `downgrade base` round-trip on a fresh Postgres | **CI failure (blocking — AE-0084)** — fails on any migration error, non-reversible revision, or 5-min timeout |
| backend / Dead Code | vulture | CI failure |
| backend / Mutation (blocking ≥75%) | mutmut + `scripts/ci/mutation-score-gate.sh` | **CI failure (blocking — AE-0049)** if mutation score < 75% |
| backend / Integrity (anti-gaming) | `scripts/ci/check-integrity.sh backend` | **CI failure (blocking)** on net-new suppressions, skipped/weakened tests, loosened thresholds, raised baselines, or prohibited DDD imports (diff-scoped; pre-existing debt never gated) |

### Architecture ratchet and baseline-down procedure

The `backend / Architecture` job enforces the modularization import boundaries
through a **single source of truth**: the committed baseline at
`.agent/reports/import-violations-baseline.md` (AE-0078), mirrored as the
`BASELINE_*` constants in `scripts/metrics/import_baseline.py`. Three pieces
work together (no second hand-maintained number):

| Mode | What it does | Where it runs |
|------|--------------|---------------|
| `import_baseline.py` (no args) | Regenerates the baseline report (stdlib-only, byte-identical on a fixed tree). | Manual / baseline-down |
| `import_baseline.py --check` | **Ratchet (enforcing).** Compares the current tree to the baseline field-exact for all six categories; exit 1 if any rises. | CI `backend / Architecture` + pre-commit |
| `import_baseline.py --summary` | **Report (non-blocking).** Markdown table of the six categories (current vs baseline) → GitHub Step Summary + `architecture-report` artifact. | CI `backend / Architecture` |
| `lint-imports` (`--emit-importlinter` regenerates `backend/.importlinter`) | The four import categories are also ratcheted by Import Linter's grandfathered `ignore_imports` lists (any NEW edge breaks CI). | CI `backend / Architecture` |

The report and the ratchet consume the same `collect_metrics()` +
`BASELINE_*` values, so they can never disagree: `--summary`'s verdict mirrors
`--check`'s exit code. When a PR raises any category above its baseline the
ratchet fails the build and the report shows the offending row as
`FAIL — rose above baseline`.

#### Ratcheting the baseline DOWN (after retiring violations)

When refactoring removes import violations (e.g. a service stops importing
infrastructure), the current counts drop below the baseline. `--check` still
**passes** (counts may decrease), and `--summary` shows the row as
`OK (ratcheted down)`. To lock in the improvement so the retired violations
can never return, ratchet the baseline down:

1. **Regenerate the baseline report** from repo root:
   ```bash
   python3 scripts/metrics/import_baseline.py > .agent/reports/import-violations-baseline.md
   ```
   (The committed report has a hand-written preamble above the
   `# Import-violation baseline (generated ...)` marker; preserve it — only the
   generated body below the marker changes. Re-paste the generated output under
   the existing preamble rather than overwriting the whole file.)
2. **Update the `BASELINE_*` constants** in
   `scripts/metrics/import_baseline.py` to the new (lower) numbers shown by
   `python3 scripts/metrics/import_baseline.py --summary`:
   `BASELINE_PAIR_CEILING` (runtime + type-checking pairs per category),
   `BASELINE_GET_CONTAINER`, and `BASELINE_COMMIT_SITES`. Also bump
   `BASELINE_COMMIT` to the commit that re-pins the artifact.
3. **Regenerate `backend/.importlinter`** so the grandfathered edge list drops
   the retired edges (run from `backend/`, needs the import-linter env):
   ```bash
   cd backend && uv run python ../scripts/metrics/import_baseline.py --emit-importlinter > .importlinter
   ```
4. **Verify** the ratchet still passes against the new baseline and the report
   matches:
   ```bash
   python3 scripts/metrics/import_baseline.py --check    # exit 0
   python3 scripts/metrics/import_baseline.py --summary  # all rows OK
   ```
5. Commit the baseline report, the updated constants, and `.importlinter`
   together in one change.

> **Never ratchet UP.** The baseline only ever decreases. Adding a new
> violation must be fixed, not baselined.

### Frontend Quality Gates (`Frontend Quality Gates` workflow)

| Job | Tool | Enforcement |
|-----|------|-------------|
| frontend / Lint | eslint `--quiet` (repo-wide errors) | CI failure |
| frontend / Lint (changed) | eslint `--max-warnings=0` on diff | CI failure |
| frontend / Type Check | tsc --noEmit | CI failure |
| frontend / Test | vitest | CI failure |
| frontend / Format | prettier --check | CI failure |
| frontend / Security | npm audit --audit-level=high | CI failure |
| frontend / Mutation (advisory) | Stryker | Non-blocking; PR summary comment |
| frontend / Legacy guard | `npm run check:legacy` | CI failure — no v1 imports in `src/app/dashboard` |
| frontend / Legacy inventory | `npm run check:legacy-inventory` | Advisory until Phase 1 complete ([plan](../plans/frontend-legacy-removal.md)) |
| frontend / Integrity (anti-gaming) | `scripts/ci/check-integrity.sh frontend` | **CI failure (blocking)** on net-new `eslint-disable`/`@ts-ignore` suppressions, skipped/focused tests, or loosened thresholds (diff-scoped) |

### Frontend legacy removal (neon shell)

| Checkpoint | How to verify | Tool/Command |
|------------|---------------|--------------|
| No `ChatInterface` in dashboard routes | Import guard | `cd frontend && npm run check:legacy` |
| No `/(create)` route group | Route guard | `npm run check:legacy` |
| Phase 1 mock/orphan files deleted | Inventory guard | `npm run check:legacy-inventory` |
| Gherkin spec for removal | Scenario review | `tests/features/frontend-legacy-removal.feature` |
| Vitest guard | Unit test | `src/scripts/legacy-removal-guard.test.ts` |

**Plan:** [docs/plans/frontend-legacy-removal.md](../plans/frontend-legacy-removal.md)

### Pre-Merge Gates (Must Pass)

| Gate | Tool | Enforcement |
|------|------|-------------|
| Lint | ruff check / eslint | CI failure |
| Blanket ignore guard | grep on `pyproject.toml` | CI failure — blocks `"src/rag_backend/**"` |
| Type check | mypy / tsc --noEmit | CI failure |
| Unit tests | pytest / vitest | CI failure |
| Diff coverage | diff-cover ≥75% (backend) | CI failure |
| Build | docker build / npm run build | CI failure (release pipelines) |
| Legacy guard (frontend) | `npm run check:legacy` | CI failure on dashboard PRs |

### Pre-Merge Gates (Should Pass / Advisory)

| Gate | Tool | Enforcement |
|------|------|-------------|
| Mutation tests (backend) | mutmut ≥75% | **CI failure (blocking — AE-0049)** |
| Mutation tests (frontend) | stryker | CI advisory job |
| Strict diff lint (backend) | ruff PLR0913/C901/PLR0912/PLR0911/PLR0914/PLR1702 on changed lines | CI failure on changed lines |
| Strict diff lint (frontend) | eslint changed | CI failure on changed files |
| Dead code | vulture | CI failure |
| Architecture boundaries | import-linter | CI failure |

### CI Hardening Gates (Backend) — AE-0049

These four gates are **blocking** (a PR cannot merge if any fails). All are
robust to empty diffs, the first commit on a branch, and fork PRs (the
`git diff`/`git fetch` calls are guarded so the step skips cleanly rather than
crashing when `origin/main` is unavailable).

| Gate | Tool / Command | Threshold | Enforcement | Notes |
|------|----------------|-----------|-------------|-------|
| Ruff blanket ignore guard | grep on `pyproject.toml` | n/a | CI failure | Blocks any `"src/rag_backend/**"` entry in `ruff.lint.per-file-ignores`. Prevents re-introduction of directory-wide ignore patterns that mask lint violations. |
| Ruff `--diff` (changed files) | `ruff check --diff` on `git diff --name-only origin/main...HEAD -- '*.py'` | zero new violations | CI failure (blocking) | Fast PR-only feedback: fails if changed `.py` files contain ruff violations. In the `backend / Lint & Format` job. |
| Strict Diff | `scripts/ci/ruff-strict-changed.sh` → `ruff --select PLR0913,C901,PLR0912,PLR0911,PLR0914,PLR1702` on **changed lines only** | max-args=3, max-complexity=10, max-branches=8, max-returns=5, max-locals=12, max-nested-blocks=4 | CI failure (blocking) | In the `backend / Strict Diff` job. Violations on pre-existing untouched lines are ignored — only changed lines fail. |
| diff-cover gate | `diff-cover coverage.xml --compare-branch=origin/main --fail-under=75` | ≥75% diff coverage | CI failure (blocking) | Enforces ≥75% coverage on changed lines. In the `backend / Test & Coverage` job. |
| Mutation gate | `scripts/ci/mutation-score-gate.sh 75` (mutmut + `export-cicd-stats`) | mutation score ≥75% | CI failure (blocking) | Score = `killed / (killed + survived + timeout + suspicious)`. Baseline ≈80.2%. In the `backend / Mutation (blocking ≥75%)` job. Per ADR-005 the 75% floor is below the business-logic "Low" (70%) buffer applied to the whole mutated set as a starting threshold. |

### Fresh-DB Migration Gate (Backend) — AE-0084

- **Schema-drift check (AE-0086):** after `upgrade head`, CI runs `alembic revision --autogenerate` and fails if the diff is non-empty — enforcing that the squashed baseline stays equal to `Base.metadata` while startup still uses `create_all`. A broken/out-of-order/non-reversible revision fails the gate inherently (non-zero alembic exit); regenerate the baseline per `backend/alembic/README.md`.

The `backend / Migrations (fresh DB)` job guards the Alembic migration chain.
It provisions an **ephemeral, empty** `postgres:16-alpine` service (no app
state, no prior migrations) and runs the full chain from scratch.

| Step | Command | Bound | Enforcement |
|------|---------|-------|-------------|
| Forward chain | `uv run alembic upgrade head` | `timeout-minutes: 5` | CI failure on any revision error or timeout |
| Reversible round-trip | `uv run alembic downgrade base` | `timeout-minutes: 5` | CI failure if any revision is non-reversible (missing/broken `downgrade()`) |

- The job lives in `Backend Quality Gates` (`.github/workflows/backend-quality-gates.yml`) — no new standalone workflow, no deployment CI changes.
- `DATABASE_URL` uses the `postgresql+asyncpg://` scheme; `alembic/env.py` rewrites it to `postgresql+psycopg://` for the sync migration engine.
- A clean chain passes; a broken or out-of-order revision (e.g. a `upgrade()` that errors on an empty DB) fails the forward step, and a non-reversible revision fails the round-trip.
- Underpins Phase 4+ migrate-in-place windows (reversible-path discipline) per the domain modularization plan.

### Nightly / Weekly Gates

| Gate | Tool | Cadence | Workflow |
|------|------|---------|----------|
| Full mutation suite (backend) | mutmut ≥75% | Weekly (Mon 04:00 UTC) + `workflow_dispatch` | `.github/workflows/mutation-weekly.yml` (ADR-005 Phase 4) |
| Full mutation suite (frontend) | stryker | Weekly | — |
| Full vulnerability scan | pip audit / npm audit | Daily (PR: high severity) | — |
| Dependency freshness | pip list --outdated | Weekly | — |
| Dead code sweep | vulture | Weekly | — |
| Maintainability index | radon mi | Weekly | — |

---

## 8. Tool Reference

### Python Backend

| Tool | Purpose | Configuration File | Command |
|------|---------|-------------------|---------|
| ruff | Linting + formatting | pyproject.toml | ruff check src/ |
| mypy | Type checking | pyproject.toml | mypy --strict src/ |
| pytest | Testing | pyproject.toml | pytest |
| mutmut | Mutation testing | pyproject.toml | mutmut run |
| xenon | Complexity monitoring | setup.cfg | xenon --max-absolute B --max-modules A --max-average A src/ |
| radon | Code metrics | setup.cfg | radon mi -s --min B src/ |
| import-linter | Architecture rules | .importlinter | lint-imports |
| dead | Dead code detection | CLI args | dead --exclude ^migrations/ src/ |
| vulture | Dead code detection | CLI args | vulture src/ --min-confidence 80 |
| pip-audit | Vulnerability scanning | CLI args | pip-audit |
| bandit | Security linting | CLI args | bandit -r src/ |
| semgrep | Static analysis | .semgrep/ | semgrep --config=auto src/ |
| truffleHog | Secret scanning | CLI args | trufflehog filesystem . |

### TypeScript Frontend

| Tool | Purpose | Configuration File | Command |
|------|---------|-------------------|---------|
| eslint | Linting | eslint.config.js | eslint src/ |
| tsc | Type checking | tsconfig.json | tsc --noEmit --strict |
| vitest | Testing | vitest.config.ts | vitest run |
| stryker | Mutation testing | stryker.config.json | stryker run |
| npm audit | Vulnerability scanning | Built-in | npm audit |

---

## 9. False Positive Management

### Suppression Mechanisms

| Tool | Mechanism | Example |
|------|-----------|---------|
| ruff | noqa comments | # noqa: ERA001 |
| mypy | type: ignore comments | # type: ignore[arg-type] |
| mutmut | __mutmut_exclude__ list | __mutmut_exclude__ = ["constants.py"] |
| dead | # dead: disable comments | # dead: disable |
| vulture | Whitelist file | vulture --whitelist whitelist.py |

### .qa-ignore File

Create a .qa-ignore file at the project root to suppress known false positives:

```ini
# .qa-ignore
# Format: tool:pattern
# Example:
# ruff:ERA001:templates/*  # Template files use Jinja comments
# mutmut:src/rag_backend/constants.py  # Constants file has trivial mutants
# vulture:src/rag_backend/api/routes/*  # Routes registered dynamically
```

### Review Cadence

- False positive suppressions should be reviewed **monthly**
- Remove suppressions when the underlying issue is resolved
- Document the reason for each suppression

---

## References

- ADR-005: Adopt Mutation Testing (../decisions/0005-adopt-mutation-testing.md)
- Architectural Quality Enforcement Guide (./architectural-quality-enforcement.md)
- OWASP Top 10:2025 (https://owasp.org/Top10/2025/)
- OWASP ASVS (https://owasp.org/www-project-application-security-verification-standard/)
- Backend AGENTS.md (../../backend/AGENTS.md)
- Frontend AGENTS.md (../../frontend/AGENTS.md)
- CLAUDE.md (Root) (../../CLAUDE.md)
