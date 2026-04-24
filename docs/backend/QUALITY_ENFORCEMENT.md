# Backend Quality Enforcement Guide

> **Scope:** Python backend (`backend/` directory)
> **Last updated:** 2026-04-24
> **Applies to:** All commits, PRs, and CI runs

---

## Table of Contents

1. [Quick Reference — Run All Checks](#1-quick-reference--run-all-checks)
2. [Type Safety (mypy)](#2-type-safety-mypy)
3. [Linting & Formatting (ruff)](#3-linting--formatting-ruff)
4. [Security Scanning](#4-security-scanning)
5. [Dead Code Detection](#5-dead-code-detection)
6. [Architecture Enforcement](#6-architecture-enforcement)
7. [Docstring Coverage](#7-docstring-coverage)
8. [CI/CD Pipeline](#8-cicd-pipeline)
9. [Pre-commit Hooks](#9-pre-commit-hooks)
10. [Decision Records](#10-decision-records)

---

## 1. Quick Reference — Run All Checks

```bash
cd backend

# One-shot: everything that runs in CI
uv run ruff check src/                    # Lint
uv run ruff format --check src/           # Format
uv run mypy src/                          # Types (from src/ dir)
uv run bandit -r src/ -f txt              # Security
uv run vulture src/ --min-confidence 80   # Dead code
uv run lint-imports                       # Architecture
uv run interrogate src/ --verbose         # Docstrings
uv run pytest --cov=rag_backend           # Tests + coverage

# Auto-fix what can be fixed
uv run ruff check src/ --fix
uv run ruff format src/
```

---

## 2. Type Safety (mypy)

### Flags Enabled

| Flag | Purpose |
|------|---------|
| `strict = true` | Baseline strict mode |
| `disallow_any_explicit = true` | Ban `typing.Any` annotations |
| `disallow_any_generics = true` | Ban bare generics (`dict`, `list` without `[...]`) |
| `warn_unreachable = true` | Detect dead code |
| `show_error_codes = true` | Precise `# type: ignore[code]` suppressions |

### Decision Tree for Dynamic Types

When you need to accept truly dynamic data:

1. **`Protocol`** — for anything with a known method signature
2. **`TypedDict`** — for structured dictionaries with known keys
3. **`object`** — for values of truly unknown type (runtime `isinstance` checks)
4. **`cast(T, value)`** — when you know the shape but mypy cannot see it
5. **`# type: ignore[any]`** — last resort, **must** include a justification comment

### Per-Module Overrides

Pydantic's `BaseModel`/`BaseSettings` use `Any` in base-class signatures. These modules have `explicit-any` disabled:

- `rag_backend.api.schemas`
- `rag_backend.api.routes.auth`
- `rag_backend.infrastructure.config.settings`

---

## 3. Linting & Formatting (ruff)

### Rule Categories Enabled

| Category | Codes | What it catches |
|----------|-------|-----------------|
| **Core** | `E`, `F`, `I`, `N`, `W` | pycodestyle, Pyflakes, isort, pep8-naming |
| **Security** | `S` | Bandit rules — hardcoded passwords, unsafe eval, missing timeouts |
| **Bug Prevention** | `BLE`, `RET`, `RSE`, `C4` | Blind except, return consistency, raise consistency, comprehensions |
| **API Quality** | `FBT`, `A`, `ERA`, `ARG`, `FAST` | Boolean trap, builtins shadow, commented-out code, unused args, FastAPI patterns |
| **Complexity** | `PLR`, `C90`, `TRY` | Pylint refactor, McCabe, tryceratops |
| **Ruff Extras** | `RUF` | Unused noqa, ambiguous unicode chars |

### Ignored Rules (with justification)

| Rule | Reason |
|------|--------|
| `B008` | FastAPI `Depends()` in argument defaults is idiomatic |
| `BLE001` | Health-check endpoints legitimately catch broad exceptions from external services |
| `S101` | `assert` is acceptable in tests (per-file ignore) |

### Complexity Thresholds

```toml
[tool.ruff.lint.mccabe]
max-complexity = 12

[tool.ruff.lint.pylint]
max-branches = 12
max-statements = 50
max-args = 6
max-returns = 6
max-locals = 15
max-nested-blocks = 5
```

---

## 4. Security Scanning

### 4.1 Bandit (AST-based Python security linter)

**Command:** `uv run bandit -r src/ -f txt`

**Config** (`pyproject.toml`):
```toml
[tool.bandit]
exclude_dirs = ["tests"]
skips = ["B101"]
```

**Checks for:**
- Hardcoded passwords (`B105`)
- Binding to all interfaces (`B104`)
- Unsafe `eval` / `exec`
- Missing HTTP timeouts (`S113` via ruff)
- `pickle` usage
- Subprocess shell injection

**Suppressions in codebase:**
- `rag_agent.py:296` — `# nosec B105` (string accumulator, not a password)
- `settings.py:50` — `# nosec B104` (default binding address, overridden in production)

### 4.2 pip-audit (dependency vulnerability scanner)

**Command:** `uv run pip-audit --desc`

**Scans:** PyPI/OSV databases for known CVEs in installed packages.

**CI integration:** Fails the build if vulnerabilities are found. JSON report uploaded as artifact.

---

## 5. Dead Code Detection

### vulture

**Command:** `uv run vulture src/ vulture_whitelist.py --min-confidence 80`

**Confidence levels:**
- `100%` — definitely unused (safe to remove)
- `80%` — likely unused (review for false positives like protocol implementations)

**False positive patterns:**
- Protocol methods (infrastructure implements them, vulture sees only the protocol definition)
- Public API exports in `__init__.py`
- Metaclasses and enum members

---

## 6. Architecture Enforcement

### import-linter

**Config:** `backend/.importlinter`

**Contracts:**

| # | Contract | Type | Status |
|---|----------|------|--------|
| 1 | Domain layer must not depend on outer layers | `forbidden` | ✅ Kept |
| 2 | Application layer must not depend on infrastructure or API | `forbidden` | ✅ Kept |
| 3 | Infrastructure layer must not depend on API | `forbidden` | ✅ Kept |
| 4 | Domain layer must have no internal import cycles | `layers` | ✅ Kept |

**Accepted exception:** `rag_backend.infrastructure.logging` is allowed from the application layer (cross-cutting concern for observability).

**Command:** `uv run lint-imports`

---

## 7. Docstring Coverage

### interrogate

**Config** (`pyproject.toml`):
```toml
[tool.interrogate]
fail-under = 80
exclude = ["tests", "build", "docs"]
ignore-init-method = true
ignore-magic = true
ignore-private = true
ignore-nested-functions = true
```

**Current status:** **95.5%** (465/487 public API elements documented)

**Command:** `uv run interrogate src/ --verbose`

---

## 8. CI/CD Pipeline

### GitHub Actions Workflow

**File:** `.github/workflows/backend-quality-gates.yml`

**Jobs (all parallel):**

| Job | Tool | Gate |
|-----|------|------|
| `lint-and-format` | ruff | Zero errors / zero unformatted files |
| `type-check` | mypy | `--strict` passes |
| `architecture` | import-linter | 4/4 contracts kept |
| `docstrings` | interrogate | ≥ 80% coverage |
| `security` | bandit + pip-audit | 0 issues + 0 vulnerabilities |
| `test` | pytest + diff-cover | All pass + ≥ 90% patch coverage |
| `dead-code` | vulture | None found |

**Triggers:**
- Push to `main` touching `backend/**`
- PR to `main` touching `backend/**`

**Features:**
- Caches uv dependencies via `astral-sh/setup-uv`
- PostgreSQL service container for integration tests
- Codecov upload (optional, requires `CODECOV_TOKEN` secret)
- Bandit JSON report uploaded as artifact

---

## 9. Pre-commit Hooks

### Installation

```bash
# Install pre-commit globally
pip install pre-commit

# Install hooks into this repo
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### Configuration

**File:** `.pre-commit-config.yaml` (project root)

```yaml
repos:
  # Generic file hygiene
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-added-large-files
      - id: check-case-conflict
      - id: check-merge-conflict
      - id: check-symlinks
      - id: check-yaml
      - id: debug-statements
      - id: end-of-file-fixer
      - id: trailing-whitespace

  # Ruff: lint + format (backend src/ and tests/ only; scripts/ excluded)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.11
    hooks:
      - id: ruff
        args: [--fix]
        files: ^backend/(src|tests)/
      - id: ruff-format
        files: ^backend/(src|tests)/

  # Security: detect hardcoded secrets
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.0
    hooks:
      - id: gitleaks

  # Architecture: import-linter (backend only)
  - repo: local
    hooks:
      - id: lint-imports
        name: Check import architecture
        entry: bash -c 'cd backend && uv run lint-imports'
        language: system
        pass_filenames: false
        files: ^backend/src/.*\.py$

  # Dead code: vulture (backend only)
  - repo: local
    hooks:
      - id: vulture
        name: Check for dead code
        entry: bash -c 'cd backend && uv run vulture src/ --min-confidence 80'
        language: system
        pass_filenames: false
        files: ^backend/src/.*\.py$
```

### Hook Design Philosophy

- **Fast, reliable hooks only** — ruff (milliseconds), gitleaks, and file hygiene run on every commit
- **Auto-fix where possible** — ruff `--fix` applies safe fixes automatically
- **Fail fast on security** — gitleaks prevents credential leaks at commit time
- **Local tools for project-specific checks** — import-linter and vulture run via `repo: local` so they use the project's locked dependencies
- **mypy is CI-only** — 268 pre-existing errors from untyped third-party libraries make it impractical as a commit hook; run `uv run mypy src/` locally before pushing

---

## 10. Decision Records

### Why `disallow_any_expr` is disabled

`disallow_any_expr` catches `Any` leaking from **every untyped third-party library call** (LangChain, LangGraph, SQLAlchemy, structlog, Pinecone, etc.). Fixing this would require `type: ignore` on nearly every line touching an external API — producing noise without value. `disallow_any_generics` is the sweet spot: it catches our mistakes while ignoring external leaks.

### Why `disallow_any_decorated` is disabled

Untyped library decorators (e.g., `@tool` from LangChain, `@app.get` from FastAPI) trigger this constantly. There is no fix without upstream stub files.

### Why some `FAST002` violations use `noqa`

FastAPI's `Annotated[...]` syntax requires parameters without defaults to come before parameters with defaults. In route handlers with `limit: int = 20` followed by `db: AsyncSession = Depends(...)`, converting `db` to `Annotated` removes its default, causing a Python syntax error. Reordering parameters would change the API signature.

### Why complexity violations use `noqa`

Functions like `build_graph` (131 statements, complexity 23) and `chat` (54 statements, 21 branches) are inherently complex because they orchestrate multi-phase pipelines with streaming/non-streaming dual paths. Proper refactoring would require extracting 20+ helper functions — a major architectural change beyond the scope of linting.

### Why logging is an accepted cross-cutting concern

`rag_backend.infrastructure.logging` is imported by the application layer. In Clean Architecture, infrastructure should not be imported by application. However, logging is a cross-cutting concern: every layer needs observability. The alternative (reimplementing logging in each layer) creates duplication. The accepted pattern is a thin logging wrapper in infrastructure that is treated as an exception.

### Why mypy is not in pre-commit hooks

The codebase has **268 pre-existing mypy errors** arising from untyped third-party libraries (LangChain, LangGraph, SQLAlchemy, etc.) and legacy patterns. Adding mypy to pre-commit would block every commit. Instead:

- **Pre-commit** runs fast, non-noisy checks: ruff, gitleaks, import-linter, vulture
- **CI** runs the full mypy `--strict` check to track progress and prevent regression on new code
- Developers can run `uv run mypy src/` locally before pushing; the error count should only go down

### Why `scripts/` is excluded from pre-commit ruff

`backend/scripts/mutation_test.py` contains hardcoded multi-line string literals (mutation targets) and uses `subprocess` intentionally. These are legitimate for a one-off testing script and would require extensive `noqa` noise to satisfy ruff. CI still checks scripts if the workflow is expanded to include them.

---

## Appendix: New Domain Types

**File:** `src/rag_backend/domain/types.py`

```python
class SparseEmbedding(TypedDict):
    indices: list[int]
    values: list[float]

class ImageResult(TypedDict):
    number: int
    status: str
    path: str
    skipped: bool

class PipelineEvent(TypedDict):
    node: str
    status: str
    phase_progress: dict[str, object] | None

class ChatEvent(TypedDict, total=False):
    type: str
    content: str
    tool: str
    result: str
    sources: list[dict[str, object]]

class StatsResponse(TypedDict):
    total_vectors: int
    dimension: int
    index_fullness: float
```

These replace `dict[str, Any]` in protocols and services with explicit, type-safe shapes.
