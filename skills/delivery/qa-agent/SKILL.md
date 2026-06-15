---
name: qa-agent
description: "Validate implementation quality across security, code quality, acceptance criteria, and completeness. Use when the user says 'run QA', 'validate the implementation', 'check my code', 'review this PR', 'run the checks', or after the Developer Skill completes. Builds a shared research pack once, then runs parallel subagents for security audit, code quality, mutation testing, acceptance criteria validation, and orphan code detection. Never use for implementation or development."
version: 1.2.0
disable-model-invocation: true
---

# QA Agent

## Purpose

Validate implementations against defined quality standards. Launches **parallel subagents** across five dimensions: security, code quality, mutation testing, acceptance criteria, and orphan code detection. Produces a consolidated QA report with PASS/FAIL/WARN per dimension, severity-graded findings, and an overall quality score.

## Prerequisites

Before running, verify:
1. The implementation to validate exists (changed files, new code)
2. Project standards are accessible: `CLAUDE.md`, `AGENTS.md`, `docs/guides/qa-checkpoints.md`
3. Development environment is available (linters, type checkers, test runners installed)
4. The plan/spec with acceptance criteria is available (for criteria validation)

## Critical Rules

### 1. Parallel Execution — Never Serial
- Launch all five validation subagents **simultaneously** in a single message
- Each subagent is independent and writes to its own report section
- Wait for all five to complete before synthesizing the final report
- If any subagent fails, note it in the report but do not block others

### 2. Evidence-Only Findings
- Every finding must include a file path and line number
- Every claim must have a reference (OWASP category, lint rule code, ADR number)
- No opinions — only facts backed by tool output or code inspection

### 3. Severity Grading
| Severity | Label | Action Required |
|----------|-------|-----------------|
| 🔴 Blocker | Must fix before merge | CI should fail |
| 🟠 Warning | Should fix before merge | CI should warn |
| 🟡 Suggestion | Nice to have | CI should inform |
| ⚪ Info | For awareness | No action needed |

### 4. Never Modify Code
- The QA Agent is **read-only** — it inspects, validates, and reports
- Do not fix issues found — report them for the Developer Skill or human to address
- Exception: If a finding is a false positive, note it in the report with justification

### 5. Report Format
The final report must include:
- **Overall Score**: Numeric (0-100) with letter grade (A-F)
- **Per-Dimension Results**: PASS/FAIL/WARN with score breakdown
- **Findings List**: Sorted by severity (blockers first)
- **Summary**: Top 3 risks and recommended next steps

## QA modes

| Mode | When |
|------|------|
| **full** (default) | T2/T3 — all five subagents |
| **lite** | T1 — security (if high-risk area), AC validation, lint/tests evidence; skip mutation/orphan unless scope warrants |
| **external** | Any tier when independence matters: the implementation was authored in the same session/agent as the QA would be, or the human requests an outside check |
| **wave** | Several related tickets completed together — one external run covering the set, with per-ticket AC validation |

Read ticket `Tier:` from `.agent/tasks/`.

## External QA orchestration (OpenCode / Codex / Cursor)

The QA dimensions can be executed by an **external LLM CLI session**
instead of same-session subagents — eliminating self-review bias when
the developer and QA would otherwise share a context. Orchestrate it
automatically:

1. Build the prompt per `references/external-qa.md` (mandatory: skill
   pointer, commit-pinned scope, read-only + verification-commands
   allowance, accepted-gaps context, tool-call budget, and the final
   `QA_VERDICT: PASS|WARN|FAIL` line requirement).
2. Run `scripts/qa/run_external_qa.sh <prompt> <out> [tool]` — it
   handles tool fallback (opencode → codex → cursor-agent), the
   OpenCode hang-at-init recovery, ANSI stripping, and verdict
   extraction (exit 0/10/20 = PASS/WARN/FAIL).
3. Loop per the verdict: FAIL → fix → full re-run; WARN → fix
   actionable findings → short confirmation round; PASS → archive with
   provenance, write per-ticket `.agent/reports/AE-####.qa.md` files
   (required by `validate_all_tickets.py` before Review), move
   ticket(s) to Review.

Reviewer priority and prompt requirements: `config.yaml`. Full runbook
incl. live progress monitoring: `references/external-qa.md`.

## Agentic Ticket QA Protocol

**Before QA:**

1. Read `.agent/tasks/AE-####.md` and `.agent/reports/AE-####.dev-summary.md`.
2. Move ticket to `QA Running`.
3. Identify changed files and acceptance criteria.

**During QA:**

1. Run QA dimensions per mode above.
2. Link findings to file:line.

**After QA:**

1. Write `.agent/reports/AE-####.qa.md` (use report header from source plan).
2. Update ticket `QA Report` section with link.
3. Status: blockers → `Needs Fixes`; warnings only or pass → `Review`; inconclusive → `Blocked`.
4. `uv run python scripts/agent_tasks/render_board.py`

## Workflow

### Phase 1: Context Loading

1. Read the plan/spec file (if available) to extract acceptance criteria
2. Read `docs/guides/qa-checkpoints.md` for the full checklist
3. Read `CLAUDE.md` and relevant `AGENTS.md` for project-specific rules
4. Identify the scope of changes (changed files, new files, modified tests)
5. If the scope is unclear, ask the user

### Phase 1.5: Build the QA Research Pack (shared context)

**Before launching the 5 reviewers, build a shared research pack once** so the
subagents skip independent codebase exploration (exploration is the dominant
token cost). Full protocol: `references/qa-research-pack.md`.

1. Run a **dedicated read-only explorer subagent** (`Explore` agent type) over
   the change scope. Its model is selectable via `config.yaml`
   `research_pack.model` (default cheap/fast, overridable to any provider — not
   locked to Anthropic).
2. It writes `.agent/reports/AE-####.qa-research.md` (or
   `.agent/reports/<wave-id>.qa-research.md` for waves) using the 10-section,
   role-tagged template, stamped with the commit SHA + diff range.
3. **Staleness**: if the diff later moves (fix round), regenerate the pack (or
   the affected sections) before re-running QA.

### Phase 2: Launch Parallel Subagents

Launch **five subagents simultaneously** in a single message. Inject the
**research pack as a shared (cacheable) prefix** to each, plus a short brief
naming the sections that matter to it (routing table in
`references/qa-research-pack.md`). Each subagent:

- reads only its assigned pack sections — **does NOT re-explore the codebase**;
- **re-verifies §10 UNKNOWNS** in its dimension and confirms any fact against
  live code before raising a finding (the pack is a map, not a verdict — this
  preserves independent verification and defeats the shared blind spot);
- writes to its dedicated report section.

#### Subagent 1 — Security Audit
**Scope**: OWASP Top 10 2025 + dependency + secret scanning

Checklist:
- [ ] **A01 Broken Access Control** — Are there authorization checks on all endpoints? Are role-based permissions enforced server-side?
- [ ] **A02 Security Misconfiguration** — Are default credentials changed? Is debug mode disabled? Are CORS settings restrictive?
- [ ] **A03 Software Supply Chain Failures** — Are there any dependencies with known vulnerabilities? Check `pip audit` / `npm audit`. Are dependencies within the 7-day update window?
- [ ] **A04 Cryptographic Failures** — Are passwords hashed (bcrypt/argon2)? Is TLS enforced? Are secrets encrypted at rest?
- [ ] **A05 Injection** — Are all user inputs parameterized? Any raw SQL/NoSQL queries? Any `eval()` or `exec()` calls?
- [ ] **A06 Insecure Design** — Are rate limits in place? Is there input validation at the API boundary?
- [ ] **A07 Authentication Failures** — Are session tokens properly managed? Is MFA available? Are password policies enforced?
- [ ] **A08 Software/Data Integrity Failures** — Are CI/CD pipelines signed? Are dependencies integrity-checked?
- [ ] **A09 Security Logging & Alerting** — Are security events logged? Are logs monitored? Is PII excluded from logs?
- [ ] **A10 Mishandling of Exceptional Conditions** — Are exceptions caught and handled? Do error messages leak stack traces?

Tools: `pip audit` / `npm audit`, `bandit` (Python), `semgrep`, `truffleHog` / `gitleaks` (secrets), manual code inspection

#### Subagent 2 — Code Quality
**Scope**: Lint rules, type safety, complexity, architecture, file size

Checklist:
- [ ] **Lint passes**: `ruff check` (backend) / `eslint` (frontend) — zero warnings
- [ ] **Type check passes**: `mypy --strict` (backend) / `tsc --noEmit` (frontend)
- [ ] **No `Any`/`object` types** — Explicit types everywhere
- [ ] **No magic strings** — All string literals in named constants
- [ ] **Early returns** — No deeply nested `if` statements
- [ ] **Max 400 lines per file** — Any file exceeding this limit
- [ ] **Cyclomatic complexity** — ruff C90: max-complexity = 10; xenon: max-absolute B
- [ ] **Cognitive complexity** — ruff PLR: max-branches 10, max-statements 40, max-nested-blocks 4
- [ ] **Dead code** — `ruff ERA001` (commented-out code), `dead` or `vulture` (unused definitions)
- [ ] **Architecture boundaries** — `import-linter` or `pytest-archon` contracts respected
- [ ] **No secrets in code** — API keys, tokens, passwords hardcoded

#### Subagent 3 — Mutation Testing
**Scope**: Test quality via mutation score

Checklist:
- [ ] **Backend**: Run `mutmut` on changed modules — target 70%+ mutation score
- [ ] **Frontend**: Run `StrykerJS` on changed components — target 70%+ mutation score (business logic), 50%+ (UI components)
- [ ] **Compare against ADR-005 thresholds**:
  - Business Logic: Break 50% | Low 70% | High 80%
  - API Routes: Break 40% | Low 60% | High 75%
  - UI Components: Break 30% | Low 50% | High 65%
- [ ] **Report surviving mutants** — List top 5 most concerning survivors with file/line
- [ ] **Check for equivalent mutants** — Flag any that are clearly equivalent (no test can kill them)

Note: Mutation testing is slow. Run on changed modules only (incremental). If full suite is requested, warn about time.

#### Subagent 4 — Acceptance Criteria Validation
**Scope**: Verify each criterion from the plan/spec is satisfied

Checklist:
- [ ] Load acceptance criteria from the plan/spec file
- [ ] For each criterion:
  - [ ] Is there a test covering it? (Gherkin scenario or test function)
  - [ ] Does the test pass? (run it specifically)
  - [ ] Does the implementation actually satisfy the criterion? (manual check)
- [ ] **Flag any criterion without a test** — Missing test coverage for acceptance criteria
- [ ] **Flag any criterion with a failing test**
- [ ] **Flag any implemented behavior not in the criteria** (scope creep)

#### Subagent 5 — Orphan & Unfinished Code Detection
**Scope**: Dead code, TODOs, stubs, incomplete implementations

Checklist:
- [ ] **Unused exports/functions** — Functions, classes, and variables defined but never imported/called
- [ ] **TODO/FIXME/HACK/XXX density** — Per-file count; flag files with 5+ unresolved markers
- [ ] **Stub implementations** — Functions with only `pass`, `raise NotImplementedError`, empty `return`
- [ ] **Commented-out code blocks** — Real code (not just comments) that is commented out
- [ ] **Orphaned files** — Files not imported or referenced by any other file
- [ ] **Unused dependencies** — Packages in `pyproject.toml`/`package.json` not imported anywhere
- [ ] **Dead event handlers** — Event listeners registered but never triggered
- [ ] **Unused route handlers** — API endpoints defined but not consumed

### Phase 3: Synthesis — Consolidated QA Report

Once all five subagents complete, produce the consolidated report:

```markdown
# QA Validation Report

## Overall Score: XX/100 (Grade X)

### Per-Dimension Results
| Dimension | Status | Score | Details |
|-----------|--------|-------|---------|
| Security | ✅ PASS / 🟠 WARN / ❌ FAIL | X/100 | n findings |
| Code Quality | ✅ / 🟠 / ❌ | X/100 | n findings |
| Mutation Testing | ✅ / 🟠 / ❌ | X/100 | n findings |
| Acceptance Criteria | ✅ / 🟠 / ❌ | X/100 | n of m criteria met |
| Orphan/Unfinished Code | ✅ / 🟠 / ❌ | X/100 | n findings |

### 🔴 Blocker Findings
1. **Title** — File:Line — Description — Reference

### 🟠 Warning Findings
...

### 🟡 Suggestion Findings
...

### ⚪ Info Findings
...

### Top 3 Risks
1. ...
2. ...
3. ...

### Recommended Next Steps
- ...
```

## References

- `references/qa-research-pack.md` — Shared research-pack pattern (Phase 1.5)
- `references/external-qa.md` — External QA orchestration runbook
- `config.yaml` — External reviewer priority and prompt requirements
- `scripts/qa/run_external_qa.sh` — Orchestrator (repo root `scripts/qa/`)
- `docs/guides/qa-checkpoints.md` — Full QA checkpoint reference
- `docs/decisions/0005-adopt-mutation-testing.md` — Mutation testing thresholds
- `docs/guides/architectural-quality-enforcement.md` — Code quality tooling
- `CLAUDE.md` — Root project standards
- `backend/AGENTS.md` — Backend-specific standards
- `frontend/AGENTS.md` — Frontend-specific standards
