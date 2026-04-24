# Backend API Quality Enforcement — Research Synthesis

> Compiled from parallel research across official documentation, GitHub repos, and engineering best-practice guides. Full raw reports are in:
> - `docs/research/cicd-quality-gates-python.md`
> - `docs/guides/architectural-quality-enforcement.md`

---

## Tier 1: Immediate Wins (Low Effort, High Impact)

These can be added to `pyproject.toml` today with minimal friction.

### 1.1 Expand Ruff Ruleset

Our current ruff `select` is `E, F, I, N, W, UP, B, SIM`. Based on research, add:

| Ruleset | Code | Why |
|---------|------|-----|
| **Security** | `S` | Bandit rules — catches hardcoded passwords, unsafe eval, missing HTTP timeouts, SSL bypass (`verify=False`) |
| **Bug Prevention** | `BLE` | Prevents `except Exception:` without specificity |
| **Return Consistency** | `RET` | Enforces consistent return patterns (early returns, no implicit None after return) |
| **Raise Consistency** | `RSE` | Catches incorrect `raise` usage |
| **Boolean Trap** | `FBT` | Prevents boolean positional args — major API usability win |
| **Builtins Shadow** | `A` | Prevents shadowing Python builtins (`id`, `type`, `list`, etc.) |
| **Comprehensions** | `C4` | Enforces efficient `list`/`dict`/`set` patterns |
| **Dead Code** | `ERA` | Flags commented-out code (replaces eradicate) |
| **Unused Args** | `ARG` | Removes dead parameters |
| **FastAPI** | `FAST` | `FAST002` (non-Annotated dependency), `FAST003` (unused path param) |
| **Pylint Refactor** | `PLR` | `too-many-branches`, `too-many-statements`, `too-many-arguments` |
| **McCabe** | `C90` | Cyclomatic complexity limit |
| **Tryceratops** | `TRY` | Better exception handling patterns |

### 1.2 mypy Flag Tuning

Already on `strict`. Add:
- `warn_unreachable = true` — detects dead code after early returns ✅ (already on)
- `local_partial_types = true` — prevents `None` inference across module scope
- `disallow_any_unimported = true` — fail on untyped imports instead of silently allowing `Any`

### 1.3 Pre-commit Hooks

Add to `.pre-commit-config.yaml`:
- **gitleaks** — prevent credential leaks at commit time
- **pip-audit** — check for known CVEs in dependencies
- **custom hook** — enforce max 400 lines per file

---

## Tier 2: Short-Term Additions (Medium Effort, High Value)

### 2.1 Security Scanning in CI
- **Bandit** (`S` rules in ruff cover most of this)
- **pip-audit** — PyPA-backed, no auth required, generates SBOMs
- Run on every PR; block merge on vulnerabilities

### 2.2 Coverage Enforcement
- **diff-cover** — enforce ≥ 90% coverage on changed lines
- Prevents "coverage by dilution" — ensures *new* code is tested

### 2.3 Docstring Coverage
- **interrogate** — enforce ≥ 80% docstring coverage on public API
- Ruff `D` rules for style (Google convention)

### 2.4 Architecture Testing
- **import-linter** — enforce Clean Architecture boundaries (domain → application → infrastructure → API)
- **pytest-archon** — architectural rules as tests

---

## Tier 3: Advanced / Periodic (High Effort, Specialized)

### 3.1 Property-Based Testing
- **Hypothesis** — test serialization/validation logic with generated inputs
- **Schemathesis** — property-based API testing from OpenAPI spec

### 3.2 Mutation Testing
- **mutmut** — assess test suite quality by introducing code mutations
- Run weekly or pre-release; very slow for daily CI

### 3.3 Complexity Metrics
- **radon + xenon** — cyclomatic complexity and maintainability index
- **ruff PLR** rules already cover branches/statements/arguments

### 3.4 Load Testing
- **k6** — best CI-native pass/fail support with thresholds
- Smoke test on PR; full suite pre-release

---

## Recommended Priority Order

| Priority | Action | Tool | Effort |
|----------|--------|------|--------|
| P0 | Expand ruff rules (S, BLE, RET, RSE, FBT, A, C4, ERA, ARG, FAST, PLR, C90, TRY) | ruff | Low |
| P0 | Add `local_partial_types` and `disallow_any_unimported` | mypy | Low |
| P0 | Fix all new ruff/mypy violations | manual | Medium |
| P1 | Add diff-cover gate (≥ 90% patch coverage) | diff-cover | Low |
| P1 | Add pip-audit to CI | pip-audit | Low |
| P1 | Add gitleaks to pre-commit | gitleaks | Low |
| P2 | Add interrogate (≥ 80% docstring coverage) | interrogate | Medium |
| P2 | Add import-linter for Clean Architecture | import-linter | Medium |
| P2 | Add pytest-archon tests | pytest-archon | Medium |
| P3 | Adopt Hypothesis for validation tests | hypothesis | Medium |
| P3 | Run mutmut weekly | mutmut | High |
| P3 | Add k6 smoke tests | k6 | Medium |

---

## Sources

- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
- [mypy Configuration](https://mypy.readthedocs.io/en/stable/config_file.html)
- [Hypermodern Python](https://blog.claudiojolowicz.com/posts/hypermodern-python-03-linting/)
- [Schemathesis](https://schemathesis.readthedocs.io/)
- [pip-audit](https://github.com/pypa/pip-audit)
- [import-linter](https://import-linter.readthedocs.io/)
- [pytest-archon](https://github.com/jwbargsten/pytest-archon)
- [mutmut](https://mutmut.readthedocs.io/)
- [k6](https://grafana.com/docs/k6/latest/)
