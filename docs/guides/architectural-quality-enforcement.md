# Architectural Quality Enforcement for Python Backends — Research Report

> Compiled for the Alter-Ego project backend. All thresholds and configurations are drawn from authoritative documentation, GitHub repositories, and community best practices.

---

## Table of Contents

1. [Import Linting & Architecture Testing](#1-import-linting--architecture-testing)
2. [Cyclomatic Complexity Limits](#2-cyclomatic-complexity-limits)
3. [Docstring Enforcement](#3-docstring-enforcement)
4. [Dead Code Detection](#4-dead-code-detection)
5. [Cognitive Complexity Limits](#5-cognitive-complexity-limits)
6. [Maintainability Index Enforcement](#6-maintainability-index-enforcement)
7. [File Size & Function Length Limits](#7-file-size--function-length-limits)
8. [Recommended Unified `pyproject.toml` Configuration](#8-recommended-unified-pyprojecttoml-configuration)
9. [CI Integration Summary](#9-ci-integration-summary)

---

## 1. Import Linting & Architecture Testing

### Tools Overview

| Tool | Purpose | Integration |
|------|---------|-------------|
| **import-linter** | Enforce architectural constraints between Python modules (forbidden imports, layers, independence, acyclic siblings) | CLI + pre-commit |
| **pytest-archon** | pytest-based architectural rule testing (inspired by Java ArchUnit) | pytest |
| **grimp** | Builds a queryable dependency graph of internal imports; powers import-linter | Programmatic / library |

### import-linter

**Source:** [import-linter.readthedocs.io](https://import-linter.readthedocs.io/en/stable/), [GitHub: seddonym/import-linter](https://github.com/seddonym/import-linter)

**Configuration (`.importlinter`):**

```ini
[importlinter]
root_package = myproject

[importlinter:contract:one]
name = Domain must not import infrastructure
type = forbidden
source_modules = myproject.domain
forbidden_modules = myproject.infrastructure

[importlinter:contract:layers]
name = Enforce layered architecture
type = layers
containers = myproject
layers =
    web
    domain
    infrastructure
```

**Contract types:** Forbidden, Protected, Layers, Independence, Acyclic siblings, Custom.

**Recommended thresholds:**
- Run `lint-imports` on every PR.
- Define one contract per architectural boundary.
- Fail CI on any contract breach (non-zero exit code).

### pytest-archon

**Source:** [GitHub: jwbargsten/pytest-archon](https://github.com/jwbargsten/pytest-archon)

**Configuration (in pytest test files):**

```python
from pytest_archon import archrule

def test_domain_has_no_dependencies():
    (
        archrule("domain", comment="domain stands alone")
        .match("myproject.domain*")
        .should_not_import("myproject*")
        .may_import("myproject.domain.*")
        .check("myproject")
    )
```

**Recommended thresholds:**
- Write one architectural test per domain boundary.
- Run as part of standard pytest suite.
- Use `only_toplevel_imports=True` for stricter checks, or `only_direct_imports=True` to skip transitive dependencies.

### grimp

**Source:** [GitHub: python-grimp/grimp](https://github.com/python-grimp/grimp)

Grimp is the underlying engine for import-linter. Use it programmatically for custom architectural checks:

```python
import grimp
graph = grimp.build_graph('myproject')
assert 'myproject.domain' not in graph.find_modules_directly_imported_by('myproject.infrastructure')
```

**Integration with ruff/mypy:**
- These tools are orthogonal to ruff/mypy. They run as separate CI steps.
- Combine with ruff's `TID` (tidy-imports) rules for import style enforcement.

---

## 2. Cyclomatic Complexity Limits

### Tools Overview

| Tool | What it measures | Integration |
|------|-----------------|-------------|
| **radon** | Cyclomatic Complexity (CC), MI, raw metrics | CLI + flake8 plugin |
| **xenon** | CI monitoring wrapper around radon | CLI + pre-commit |
| **ruff C90** | McCabe complexity directly in the linter | ruff |

### radon

**Source:** [radon.readthedocs.io](https://radon.readthedocs.io/en/latest/)

Radon computes CC based on the AST. Each decision point adds +1.

**CC score → Rank mapping:**

| CC Score | Rank | Risk |
|----------|------|------|
| 1–5 | A | Low — simple block |
| 6–10 | B | Low — well structured |
| 11–20 | C | Moderate — slightly complex |
| 21–30 | D | More than moderate |
| 31–40 | E | High — alarming |
| 41+ | F | Very high — error-prone |

**CLI usage:**

```bash
radon cc -s --min B src/
radon cc -a src/  # show average
```

**Configuration (`radon.cfg` or `setup.cfg`):**

```ini
[radon]
cc_min = B
cc_max = F
exclude = tests*,docs*
```

**Recommended thresholds:**
- **Per function:** CC ≤ 10 (Rank B). Functions with CC ≥ 15 should be refactored.
- **Per module average:** CC ≤ 5 (Rank A).
- **No block above Rank C** in production code.

### xenon

**Source:** [GitHub: rubik/xenon](https://github.com/rubik/xenon)

Xenon is a radon wrapper designed for CI. It exits non-zero when thresholds are breached.

**CLI usage:**

```bash
xenon --max-absolute B --max-modules A --max-average A src/
```

**pre-commit configuration:**

```yaml
- repo: https://github.com/rubik/xenon
  rev: v0.9.0
  hooks:
  - id: xenon
    args: ['--max-absolute=B', '--max-modules=A', '--max-average=A']
```

**Recommended thresholds:**
- `--max-absolute B` (no function above CC 10)
- `--max-modules A` (no module average above CC 5)
- `--max-average A` (global average below CC 5)

### ruff C90 (McCabe)

**Source:** [Ruff Rules — mccabe (C90)](https://docs.astral.sh/ruff/rules/#mccabe-c90)

Ruff re-implements mccabe complexity checking natively.

**Configuration (`pyproject.toml`):**

```toml
[tool.ruff.lint.mccabe]
max-complexity = 10
```

**Recommended thresholds:**
- `max-complexity = 10` for backend services (same as flake8 default).
- Consider `max-complexity = 8` for stricter projects.

**Integration:**
- Ruff replaces flake8 + radon CC checks in the linter layer.
- Use xenon or radon in CI for aggregate/average enforcement.

---

## 3. Docstring Enforcement

### Tools Overview

| Tool | Purpose | Status |
|------|---------|--------|
| **pydocstyle** | PEP 257 docstring style checker | Deprecated (Nov 2023); use ruff D rules |
| **ruff D** | Native pydocstyle re-implementation | Active, recommended |
| **darglint** | Validates docstrings match function signatures | Archived (Dec 2022); limited maintenance |

### ruff D Rules (pydocstyle)

**Source:** [Ruff Rules — pydocstyle (D)](https://docs.astral.sh/ruff/rules/#pydocstyle-d), [GitHub: PyCQA/pydocstyle](https://github.com/PyCQA/pydocstyle)

The pydocstyle project is officially deprecated and recommends migrating to ruff.

**Key rules (selected):**

| Code | Description |
|------|-------------|
| D100 | Missing docstring in public module |
| D101 | Missing docstring in public class |
| D102 | Missing docstring in public method |
| D103 | Missing docstring in public function |
| D105 | Missing docstring in magic method |
| D107 | Missing docstring in `__init__` |
| D200 | One-line docstring should fit on one line |
| D400 | First line should end with a period |
| D401 | First line should be in imperative mood |
| D403 | First word of the first line should be properly capitalized |

**Configuration (`pyproject.toml`):**

```toml
[tool.ruff.lint]
select = ["D"]

[tool.ruff.lint.pydocstyle]
convention = "google"  # or "numpy", "pep257"
```

**Recommended thresholds:**
- Enable all `D` rules (`select = ["D"]`).
- Choose a convention (`google`, `numpy`, or `pep257`) for consistency.
- Ignore `D105` (magic methods) and `D107` (`__init__`) if using type annotations heavily.

### darglint

**Source:** [GitHub: terrencepreilly/darglint](https://github.com/terrencepreilly/darglint)

Darglint checks that docstring parameters/returns/raises match the actual function signature.

**Configuration (`.darglint` or `setup.cfg`):**

```ini
[darglint]
strictness=short
docstring_style=google
ignore=DAR402
```

**Strictness levels:**
- `short`: One-line descriptions acceptable.
- `long`: Allows missing Args/Returns if description is one line.
- `full`: Complete validation (default).

**Recommended thresholds:**
- Use `strictness=long` for gradual adoption.
- Use `strictness=full` for greenfield projects.
- Note: project is archived; consider pydoclint (DOC rules in ruff) as a modern alternative.

**Integration with ruff/mypy:**
- Ruff D rules cover style; darglint/pydoclint covers signature correctness.
- Mypy handles type correctness; docstring types should align with mypy annotations.
- Ruff's `ANN` (flake8-annotations) rules ensure type annotations exist, reducing the need for docstring type duplication.

---

## 4. Dead Code Detection

### Tools Overview

| Tool | What it finds | Integration |
|------|--------------|-------------|
| **vulture** | Unused code (functions, classes, variables) | CLI + pre-commit |
| **eradicate** | Commented-out code | ruff ERA001 / pre-commit |
| **dead** (asottile) | Simple dead code detection via AST | CLI + pre-commit |

### eradicate

**Source:** [GitHub: PyCQA/eradicate](https://github.com/PyCQA/eradicate)

Removes commented-out code. Integrated into ruff as rule `ERA001`.

**Ruff configuration:**

```toml
[tool.ruff.lint]
select = ["ERA"]
```

**CLI (standalone):**

```bash
eradicate --in-place example.py
```

**pre-commit:**

```yaml
- repo: https://github.com/PyCQA/eradicate
  rev: 3.0.1
  hooks:
  - id: eradicate
```

**Recommended thresholds:**
- Zero tolerance for commented-out code in production files.
- Use `# dead: disable` or ruff `noqa: ERA001` for intentional historical comments.

### dead (asottile)

**Source:** [GitHub: asottile/dead](https://github.com/asottile/dead), [PyPI](https://pypi.org/project/dead/)

Simple dead code detection that parses ASTs and reports unreferenced definitions.

**CLI:**

```bash
dead --exclude '^migrations/' --tests '(^|/)(tests?|testing)/'
```

**pre-commit:**

```yaml
- repo: https://github.com/asottile/dead
  rev: v2.1.0
  hooks:
  - id: dead
```

**Recommended thresholds:**
- Run on every PR. Review false positives (interfaces, metaclasses, enums) carefully.
- Use `# dead: disable` to suppress known false positives.

**Integration with ruff/mypy:**
- Ruff's `F` (Pyflakes) rules catch unused imports and variables.
- Ruff's `ARG` (flake8-unused-arguments) catches unused function arguments.
- Combine with `dead` or `vulture` for deeper dead-code analysis beyond single-file scope.

---

## 5. Cognitive Complexity Limits

### Tools Overview

| Tool | Purpose | Integration |
|------|---------|-------------|
| **flake8-cognitive-complexity** | Cognitive complexity scoring | flake8 plugin (not available in ruff as a dedicated category) |
| **ruff PLR** | Pylint refactor rules including branches, locals, nested blocks, statements | Native ruff |

### flake8-cognitive-complexity

**Note:** This was originally available as a flake8 plugin. Ruff does not yet have a dedicated cognitive-complexity rule category (`CYC`). However, ruff's Pylint refactor rules (`PLR`) provide effective proxies.

**Recommended thresholds (community standard):**
- Cognitive complexity ≤ 15 per function.
- Cognitive complexity ≤ 10 for critical/core business logic.

### ruff PLR Rules (Pylint Refactor)

**Source:** [Ruff Rules — Pylint (PL)](https://docs.astral.sh/ruff/rules/#pylint-pl)

These rules approximate cognitive complexity enforcement:

| Code | Description | Default |
|------|-------------|---------|
| PLR0912 | too-many-branches | 12 |
| PLR0913 | too-many-arguments | 5 |
| PLR0915 | too-many-statements | 50 |
| PLR0904 | too-many-public-methods | 20 |
| PLR0911 | too-many-return-statements | 6 |
| PLR0916 | too-many-boolean-expressions | 5 |

**Configuration (`pyproject.toml`):**

```toml
[tool.ruff.lint.pylint]
max-branches = 12
max-statements = 50
max-args = 5
max-returns = 6
max-locals = 15
max-nested-blocks = 5
```

**Recommended thresholds for backend services:**
- `max-branches = 10` (stricter than default 12)
- `max-statements = 40` (stricter than default 50)
- `max-args = 5` (keep default)
- `max-locals = 15`
- `max-nested-blocks = 4` (reduce nesting)

**Integration with ruff/mypy:**
- All PLR rules are native to ruff; no external tools needed.
- These are purely structural checks; mypy handles type complexity.

---

## 6. Maintainability Index Enforcement

### Tools Overview

| Tool | Purpose | Integration |
|------|---------|-------------|
| **radon MI** | Computes Maintainability Index (0–100) | CLI |

### radon MI

**Source:** [radon.readthedocs.io — MI command](https://radon.readthedocs.io/en/latest/commandline.html#the-mi-command)

The Maintainability Index (MI) is a composite metric based on:
- Halstead Volume (V)
- Cyclomatic Complexity (G)
- Source Lines of Code (L)
- Comment percentage (C)

**MI score → Rank mapping:**

| MI Score | Rank | Maintainability |
|----------|------|-----------------|
| 100–20 | A | Very high |
| 19–10 | B | Medium |
| 9–0 | C | Extremely low |

**CLI usage:**

```bash
radon mi -s src/
radon mi --min B src/  # only show files below rank B
```

**Configuration (`setup.cfg`):**

```ini
[radon]
mi_min = A
mi_max = C
```

**Recommended thresholds:**
- **All production modules should have MI ≥ 20 (Rank A).**
- Flag any module dropping below Rank B (MI < 10) for immediate refactoring.
- Track MI trends in CI; prevent degradation.

**Integration with ruff/mypy:**
- radon MI is an aggregate metric; it does not integrate directly with ruff or mypy.
- Run `radon mi` as a separate CI step or in pre-commit.
- Ruff's structural rules (C90, PLR) and formatting indirectly improve MI by reducing complexity and SLOC.

---

## 7. File Size & Function Length Limits

### Tools Overview

| Tool / Mechanism | What it enforces | Integration |
|------------------|-----------------|-------------|
| **ruff PLR0915** | too-many-statements | ruff |
| **ruff E501** | line length | ruff |
| **Custom scripts / pre-commit** | file line count | pre-commit |
| **pydocstyle / ruff D** | docstring line length | ruff |

### Function Length (Statements)

**Source:** [Ruff — too-many-statements (PLR0915)](https://docs.astral.sh/ruff/rules/too-many-statements/)

```toml
[tool.ruff.lint.pylint]
max-statements = 50
```

**Recommended thresholds:**
- `max-statements = 40` for backend services.
- A function should fit on one screen (~50 lines including docstring).
- Break functions exceeding 40 statements into smaller helpers.

### File Size

Ruff does not natively enforce file size limits. Use a custom pre-commit hook or CI script:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
  - id: max-file-lines
    name: Check file line count
    entry: bash -c 'find src -name "*.py" | while read f; do lines=$(wc -l < "$f"); if [ "$lines" -gt 400 ]; then echo "$f: $lines lines (max 400)"; exit 1; fi; done'
    language: system
    pass_filenames: false
```

**Recommended thresholds:**
- **Max 400 lines per file** (matches Alter-Ego CLAUDE.md rule).
- **Max 50 lines per function** (including docstring and blank lines).
- **Max 120 characters per line** (ruff default is 88; backend teams often use 100–120).

### Line Length

```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint.pycodestyle]
max-line-length = 100
```

**Integration with ruff/mypy:**
- Ruff handles both line length and statement count.
- File size limits require custom scripts or pre-commit hooks.
- Mypy is unaffected by file size but benefits from smaller, well-typed modules.

---

## 8. Recommended Unified `pyproject.toml` Configuration

```toml
[tool.ruff]
target-version = "py311"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E", "W", "F", "I", "N", "D", "UP", "B", "C4", "SIM",
    "ERA", "PLR", "C90", "ANN", "S", "ASYNC", "T20",
    "ARG", "TID", "RUF",
]
ignore = [
    "D100",  # Missing docstring in public module (optional)
    "D105",  # Missing docstring in magic method
    "D107",  # Missing docstring in __init__
    "ANN101", # Missing type annotation for self (deprecated in ruff)
    "ANN102", # Missing type annotation for cls (deprecated in ruff)
]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-branches = 10
max-statements = 40
max-args = 5
max-returns = 6
max-locals = 15
max-nested-blocks = 4

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.pycodestyle]
max-line-length = 100

[tool.ruff.format]
docstring-code-format = true
```

**Additional CI steps:**

```bash
# Import architecture
lint-imports

# Cyclomatic complexity average
xenon --max-absolute=B --max-modules=A --max-average=A src/

# Maintainability index
radon mi -s --min B src/

# Dead code
dead --exclude '^migrations/'

# Type checking
mypy --strict src/
```

---

## 9. CI Integration Summary

| Check | Tool | When to run |
|-------|------|-------------|
| Lint & format | ruff | Pre-commit + CI |
| Type check | mypy | CI |
| Import architecture | import-linter / pytest-archon | CI |
| Cyclomatic complexity (per function) | ruff C90 | Pre-commit + CI |
| Cyclomatic complexity (average) | xenon | CI |
| Maintainability index | radon mi | CI (weekly trend) |
| Dead code | dead / vulture | CI (weekly) |
| Commented-out code | ruff ERA001 | Pre-commit + CI |
| Docstring style | ruff D | Pre-commit + CI |
| Function length | ruff PLR0915 | Pre-commit + CI |
| File size | Custom pre-commit hook | Pre-commit + CI |

---

## Sources

1. **import-linter** — Documentation: https://import-linter.readthedocs.io/en/stable/ | GitHub: https://github.com/seddonym/import-linter
2. **pytest-archon** — GitHub: https://github.com/jwbargsten/pytest-archon
3. **grimp** — GitHub: https://github.com/python-grimp/grimp
4. **radon** — Documentation: https://radon.readthedocs.io/en/latest/ | CC/MI thresholds: https://radon.readthedocs.io/en/latest/commandline.html
5. **xenon** — GitHub: https://github.com/rubik/xenon
6. **ruff** — Rules: https://docs.astral.sh/ruff/rules/ | Settings: https://docs.astral.sh/ruff/settings/
7. **pydocstyle** — GitHub: https://github.com/PyCQA/pydocstyle (deprecated, recommends ruff)
8. **darglint** — GitHub: https://github.com/terrencepreilly/darglint (archived)
9. **eradicate** — GitHub: https://github.com/PyCQA/eradicate
10. **dead** — PyPI: https://pypi.org/project/dead/ | GitHub: https://github.com/asottile/dead
11. **Ruff PLR0915** — https://docs.astral.sh/ruff/rules/too-many-statements/
12. **Ruff PLR0912** — https://docs.astral.sh/ruff/rules/too-many-branches/
