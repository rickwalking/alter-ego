---
name: developer-skill
description: "Implement task details from plans following project standards. Use when the user says 'develop this task', 'implement the plan', 'work on this ticket', 'start development', 'do the wave', or after a plan has been created. Follows SDD (Spec-Driven Development): reads specs first, implements in increments, self-verifies, and reproduces the CI gates (scripts/ci/gates.sh) + anti-gaming scan green before handing off. Supports wave mode: implement a group of tickets then loop with automated external QA until convergence. Never use for code review or QA validation."
version: 1.3.0
disable-model-invocation: true
---

# Developer Skill

## Purpose

Implement task details from plans/designs following the project's standards (CLAUDE.md, AGENTS.md, ADRs). Uses **Specification-Driven Development (SDD)** — specifications (plans, ADRs, .feature files) drive all implementation decisions. Self-verifies before marking done and asks for guidance when specs are ambiguous.

## Prerequisites

Before running, verify the following exist:
1. A task/plan file (`.md`) with clear acceptance criteria
2. Access to project standards: `CLAUDE.md`, `AGENTS.md`, `docs/decisions/`, `docs/guides/`
3. Development environment is set up (dependencies installed, database running if needed)

## Critical Rules

### 1. Read Standards First — Always
- Read `CLAUDE.md` (root) and the sub-project's `CLAUDE.md` + `AGENTS.md` before writing any code
- Read relevant ADRs from `docs/decisions/` — they contain architecturally significant decisions
- Read relevant guides from `docs/guides/` for specific patterns (testing, validation, styling)

### 2. SDD (Spec-Driven Development) — Specs Drive Everything
- **Read the plan/spec first** — Understand all acceptance criteria before touching code
- **Write/update specs before code** — If the plan references `.feature` files, update them first
- **One acceptance criterion at a time** — Implement, test, verify, then move to the next
- **If specs are ambiguous, stop and ask** — Do not guess; ask the user for clarification

### 3. No Fabrication
- **Every claim in code must trace back to the spec** — If the spec says X, implement X. Do not add scope.
- **If you discover an issue during implementation**, report it — do not silently work around it
- **Never add features not in the acceptance criteria**

### 4. Self-Verification Before Completion
After implementing each criterion, run:
- **Lint**: `ruff check` (backend) / `eslint` (frontend)
- **Type check**: `mypy --strict` (backend) / `tsc --noEmit` (frontend)
- **Tests**: `pytest` (backend) / `npm test` (frontend) — all must pass
- **File size**: No files over 400 lines (per CLAUDE.md rule)
- **No magic strings**: All string literals extracted to named constants

**Before handing off to QA, reproduce the CI gates and the integrity scan — and
be green:**
```bash
bash scripts/ci/gates.sh backend --changed-only   # (or frontend / full run)
bash scripts/ci/check-integrity.sh backend        # net-new gaming → fix it
```
QA runs these same scripts and **will not pass** a failing gate. **Do not** make
CI green by gaming it — no new `# noqa` / `# type: ignore` / `# nosec` /
`# pragma: no cover` / `eslint-disable`, no new per-file-ignores or `ignore_errors`
overrides, no lowered thresholds, no skipped tests, no imports across DDD layers.
If a gate is genuinely wrong, raise it as a finding for human review (and, only
with explicit ticket justification, mark the line `# integrity-ok: <reason>`) —
never suppress silently.

### 5. Ask for Guidance When
- Acceptance criteria are ambiguous or contradictory
- The spec references a technology/pattern you're unsure about
- A decision would affect the architecture (cross-cutting concern)
- You discover the plan is inconsistent with existing ADRs

### 6. Commit Hygiene
- One commit per acceptance criterion (or logical unit)
- Conventional commit format: `type(scope): description`
- Never commit secrets, API keys, or `.env` files
- Never force-push or amend commits unless explicitly asked

## Work tier routing

Read `Tier:` from `.agent/tasks/` ticket (default T2 if absent).

| Tier | Ticket protocol |
|------|-----------------|
| T0 | No ticket required; skip BOARD updates |
| T1 | Minimal ticket (`_template.hotfix.md`); update progress + test evidence |
| T2/T3 | Full Agentic Ticket Protocol below |

## Agentic Ticket Protocol

**Before coding:**

1. Read `.agent/active-task.md` and the active ticket under `.agent/tasks/`.
2. Verify acceptance criteria and implementation plan exist (T2+).
3. `uv run python scripts/agent_tasks/move_ticket.py AE-#### --status "In Development"` (or update Status manually).
4. Add timestamped entry to ticket `Progress Log`.
5. Record branch/worktree in ticket.

**During coding:**

1. One acceptance criterion at a time.
2. Update `Progress Log`, `Files Touched`, `Test Evidence` after each verification run.
3. Do not mark criteria `[x]` until code and tests exist.

**After coding:**

1. **Gate precondition (hard) — reproduce CI before claiming done:**
   ```bash
   bash scripts/ci/gates.sh <scope>            # PASS, or SKIP only where a service is absent
   bash scripts/ci/check-integrity.sh <scope>  # zero net-new blockers
   ```
   Do **not** advance to `Dev Complete` while any gate FAILs or the integrity
   scan reports a net-new blocker. Fix the underlying issue — never suppress,
   skip, loosen a threshold, or import across a DDD layer to go green. Capture
   the `GATES_JSON:` line and the integrity result for the dev-summary.
2. Status → `Dev Complete` via `move_ticket.py` (only once step 1 is green).
3. Write `.agent/reports/AE-####.dev-summary.md` (see template below), including
   the Gate Reproduction + Integrity evidence. Create `.agent/reports/` if absent.
4. `uv run python scripts/agent_tasks/render_board.py`
5. Hand off to `/qa-agent`.

### Developer completion report template

```markdown
## Developer Completion Report
Ticket: AE-####
Status: Dev Complete

### Acceptance Criteria Implemented
- [x] ...

### Files Changed
- ...

### Tests Run
\`\`\`bash
...
\`\`\`

### Gate Reproduction (scripts/ci/gates.sh)
Paste the `GATES_JSON:` summary line(s). Every gate PASS, or SKIP only where a
service is genuinely unavailable locally (name which, and that CI will run it).
\`\`\`
GATES_JSON: {"pass":N,"fail":0,"skip":M,"results":[...]}
\`\`\`

### Integrity (scripts/ci/check-integrity.sh)
Net-new blockers: 0. (List any `integrity-ok:` markers used and their ticket
justification, or "none".)

### Deviations
None.

### Known Risks
None.

### Suggested Next Step
Run QA Agent for AE-####.
```

## Wave mode (batch tickets + automated external QA loop)

When given a **group of related tickets** (a "wave"), or when the user says
"do the wave" / "complete the wave, QA, fix, re-QA until ready", run the
automated `dev → QA → fix → re-QA` loop. Full protocol: `references/wave-loop.md`.

1. **Order** — topologically sort the wave by `Blocked-by`/`Blocks` (cycle → escalate).
2. **Implement** — run the SDD loop per ticket in dependency order; implement the
   **whole wave before QA** so integration issues surface.
3. **Reproduce gates** — run `gates.sh` + `check-integrity.sh` over the wave and
   make them green **before** paying for external QA (Step 2.5 in the runbook).
4. **QA** — one **batch** external pass over the wave (`scripts/qa/run_external_qa.sh`),
   findings tagged per ticket; build the prompt per `qa-agent/references/external-qa.md`.
5. **Loop** — read `QA_VERDICT`:
   - **FAIL** → fix blockers → regenerate research pack if files moved → full re-QA.
     **Pause for the human on the FIRST FAIL of each wave.**
   - **WARN** → fix actionable findings → verify-only confirmation round.
   - **PASS** → require ≥ 2 total passes, then a confirmation round → done.
6. **Safeguards** — MIN 2 passes, MAX 5 iterations, escalate on repeated-finding
   fingerprint or findings-count plateau. (Thresholds in `qa-agent/config.yaml`.)

For a single ticket, use the default single-ticket SDD flow below.

## Workflow

### Phase 1: Context Loading

1. Read the task/plan file thoroughly (and `.agent/tasks/` ticket when present)
2. Read `CLAUDE.md` (root), sub-project `CLAUDE.md`, and `AGENTS.md`
3. Read relevant ADRs from `docs/decisions/`
4. Read relevant guides from `docs/guides/`
5. Identify all acceptance criteria and list them explicitly
6. If anything is unclear, ask the user before proceeding

### Phase 2: Implementation (SDD Loop)

For each acceptance criterion:

1. **Spec first**: Update `.feature` files or spec documents if they exist
2. **Implement**: Write the minimal code to satisfy the criterion
3. **Test**: Write/update tests that cover the criterion (happy path + edge cases + failures)
4. **Verify**: Run lint, type check, and tests
5. **Commit**: Conventional commit message
6. **Repeat** for the next criterion

### Phase 3: Final Verification

1. **Reproduce the CI gates**: `bash scripts/ci/gates.sh <scope>` — every gate
   must be PASS (or SKIP only where a service is genuinely unavailable locally).
2. **Run the integrity scan**: `bash scripts/ci/check-integrity.sh <scope>` —
   zero net-new blockers. Fix the underlying issue; never suppress to go green.
3. Verify no files exceed 400 lines and no magic strings were introduced.
4. Report completion with:
   - List of acceptance criteria implemented
   - Any deviations from the original plan (with justification)
   - Any uncovered issues discovered during implementation
   - Confirmation that `gates.sh` + `check-integrity.sh` are green
   - Suggestion to run `/qa-agent` for full validation

## References

- `scripts/ci/gates.sh` — reproduce the CI quality gates locally (run before QA)
- `scripts/ci/check-integrity.sh` — anti-gaming scan (run before QA)
- `references/wave-loop.md` — Wave mode: batch dev + automated external QA loop
- `CLAUDE.md` — Root project standards
- `docs/decisions/` — Architecture Decision Records
- `docs/guides/` — Development guides (testing, styling, validation)
- `docs/architecture/` — System architecture documentation
- `backend/AGENTS.md` — Backend-specific standards
- `frontend/AGENTS.md` — Frontend-specific standards
