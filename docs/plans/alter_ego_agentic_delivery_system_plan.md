# Alter-Ego Agentic Delivery System Plan

**Project:** Alter-Ego
**Purpose:** Implementation context for building a persistent, visual, multi-agent delivery workflow using Kanban, repo-backed tickets, plans, QA reports, and agent skills.
**Intended use:** Inject this file as context into Claude Code, OpenCode, Codex, Cline, or another coding agent before implementation.

---

## 1. Objective

Implement an **Agentic Delivery System** for Alter-Ego where agents can:

1. Break work into properly scoped tickets.
2. Attach clear plans and acceptance criteria.
3. Work in isolated branches or worktrees.
4. Update progress in durable files.
5. Run DEV → QA loops.
6. Surface visual progress through a Kanban board.
7. Preserve evidence: tests, diffs, decisions, logs, QA reports, and final summaries.

The target model is:

```text
Kanban board = visual orchestration
Ticket files = persistent memory
Git = source of truth for code changes
QA report = quality gate
Human = final merge/release gate
```

The project already has a useful foundation:

- Root `CLAUDE.md`
- Backend/frontend `AGENTS.md`
- Existing `developer-skill`
- Existing `qa-agent`
- Existing knowledge and carousel-related skills

The missing layer is persistent task orchestration, ticket shaping, planning, board synchronization, and release governance.

---

## 2. Core Design Principles

### 2.1 Do not rely on agent memory

Agents should not depend on conversational memory or internal todo lists as the source of truth.

Use:

```text
.agent/tasks/*.md
.agent/BOARD.md
.agent/reports/*.md
docs/plans/*.md
docs/decisions/*.md
```

as durable, inspectable, versioned state.

### 2.2 Separate visual state from canonical state

The visual board is for humans and orchestration.

The repo files are the canonical record.

```text
Cline Kanban / Vibe Kanban / other board
  = visual execution layer

.agent/tasks/*.md
  = canonical ticket state

Git branch / worktree
  = implementation state

QA report
  = quality evidence
```

### 2.3 Human remains the final authority

Agents may plan, implement, test, review, and prepare PRs, but they should not auto-merge high-risk changes.

Human review is required for:

- Merge approval
- Release approval
- Security-sensitive changes
- Database migrations
- Authentication/authorization changes
- Prompt/model behavior changes
- Deployment changes

---

## 3. Proposed Repository Structure

Add the following structure:

```text
alter-ego/
  .agent/
    BOARD.md
    active-task.md
    config.yaml

    tasks/
      _template.md
      AE-0001-agentic-delivery-system.md
      AE-0002-ticket-schema.md

    reports/
      AE-0001.qa.md
      AE-0001.dev-summary.md

    logs/
      AE-0001.progress.md

  docs/
    plans/
      agentic-delivery-system.md

    decisions/
      0008-agentic-delivery-workflow.md

    guides/
      agentic-team-operating-model.md
      ticket-writing-guide.md
      kanban-agent-workflow.md

  skills/
    planner-skill/
      SKILL.md

    architect-skill/
      SKILL.md

    ticket-writer-skill/
      SKILL.md

    orchestrator-skill/
      SKILL.md

    release-manager-skill/
      SKILL.md

    developer-skill/
      SKILL.md

    qa-agent/
      SKILL.md

  scripts/
    agent_tasks/
      create_ticket.py
      move_ticket.py
      validate_ticket.py
      validate_all_tickets.py
      render_board.py
      summarize_ticket.py
```

Notes:

- Use `/docs` for formal documentation and ADRs.
- Use `.agent/` for operational delivery state.
- Use `skills/` for role-specific agent behavior.
- Use `scripts/agent_tasks/` for validation and board automation.

---

## 4. High-Level Workflow

```text
Human / Product request
        ↓
Planner Agent
        ↓
Architect Agent
        ↓
Ticket Writer Agent
        ↓
Kanban card + repo ticket file
        ↓
Developer Agent
        ↓
QA Agent
        ↓
Fix loop if needed
        ↓
Human review
        ↓
Commit / PR / merge
        ↓
Release + documentation update
```

The canonical flow:

```text
Intake
  ↓
Shaping
  ↓
Ready
  ↓
Planning
  ↓
In Development
  ↓
Dev Complete
  ↓
QA Running
  ↓
Needs Fixes ──→ In Development
  ↓
Review
  ↓
Ready to Merge
  ↓
Done
```

---

## 5. Agent Team Design

### 5.1 Delivery Orchestrator Agent

**Purpose:** Own the delivery workflow, ticket state, dependencies, and handoffs.

Responsibilities:

```text
- Create and update ticket files
- Keep .agent/BOARD.md synchronized
- Assign work to Planner, Architect, Developer, QA, or Release Manager
- Enforce WIP limits
- Detect blocked tickets
- Prevent multiple agents from editing the same files without coordination
- Maintain dependency chains
- Route failed QA work back to Developer
```

Restrictions:

```text
- Does not implement production code
- Does not modify business logic
- Does not mark tickets Done without required evidence
```

Expected outputs:

```text
- Updated .agent/BOARD.md
- Updated ticket status
- Handoff notes
- Blocker notes
```

---

### 5.2 Planner Agent

**Purpose:** Convert fuzzy product or technical requests into actionable epics and tickets.

Responsibilities:

```text
- Clarify goal, scope, non-goals, and risks
- Break work into small implementation tickets
- Define user value
- Define acceptance criteria
- Identify backend, frontend, docs, testing, and migration impacts
- Identify dependencies between tickets
- Mark tickets Ready only when they are implementable
```

Restrictions:

```text
- Does not write code
- Does not change source files
- Does not create vague tickets without acceptance criteria
```

Expected outputs:

```text
- Epic summary
- Ticket list
- Dependencies
- Risks
- Suggested implementation order
```

---

### 5.3 Architect Agent

**Purpose:** Validate the technical approach before implementation.

Responsibilities:

```text
- Read root CLAUDE.md
- Read local backend/frontend CLAUDE.md and AGENTS.md when relevant
- Check existing ADRs
- Decide whether a new ADR is required
- Define API contracts, database impacts, state-machine impacts, and integration points
- Identify feature flag, rollout, and rollback strategy
- Identify testing strategy
```

Restrictions:

```text
- Does not implement unless explicitly switched into Developer role
- Does not skip ADR checks for architecturally significant changes
```

Expected outputs:

```text
- Technical plan
- Affected modules
- API contracts
- Data model changes
- ADR required: yes/no
- Testing strategy
- Rollout strategy
```

---

### 5.4 Ticket Writer Agent

**Purpose:** Convert plans into properly scoped ticket files.

Responsibilities:

```text
- Create .agent/tasks/AE-xxxx-title.md
- Add goal, problem, scope, non-goals, and acceptance criteria
- Add Gherkin scenarios when behavior changes
- Add implementation notes
- Add affected areas
- Add QA checklist
- Add dependencies
- Add suggested commands
```

Restrictions:

```text
- Does not write production code
- Does not mark tickets Ready if required fields are missing
```

Expected outputs:

```text
.agent/tasks/AE-xxxx-title.md
```

---

### 5.5 Developer Agent

**Purpose:** Implement tickets according to the project standards.

This project already has `developer-skill`. Extend it to be ticket-aware.

Additional responsibilities:

```text
Before coding:
- Read active ticket file
- Move ticket to In Development
- Add start timestamp to Progress Log
- Record branch/worktree

During coding:
- Update Progress Log after each acceptance criterion
- Update Files Touched
- Update Test Evidence after verification runs
- Do not mark acceptance criteria complete unless code and tests exist

After coding:
- Move ticket to Dev Complete
- Write .agent/reports/AE-xxxx.dev-summary.md
- Suggest QA Agent handoff
```

Expected final report:

```markdown
## Developer Completion Report

Ticket: AE-xxxx
Status: Dev Complete

### Acceptance Criteria Implemented

- [x] ...
- [x] ...

### Files Changed

- ...

### Tests Run

```bash
...
```

### Deviations

None.

### Known Risks

None.

### Suggested Next Step

Run QA Agent for AE-xxxx.
```

---

### 5.6 QA Agent

**Purpose:** Validate completed work.

This project already has `qa-agent`. Extend it with persistent reports and ticket transitions.

Additional responsibilities:

```text
Before QA:
- Read ticket file
- Read developer summary
- Identify changed files
- Move ticket to QA Running

During QA:
- Run the existing QA dimensions
- Store evidence for each dimension
- Link file paths and line numbers for findings

After QA:
- Write .agent/reports/AE-xxxx.qa.md
- If blockers exist, move ticket to Needs Fixes
- If warnings only, move ticket to Review with WARN
- If all pass, move ticket to Review
```

Status mapping:

```text
Any blocker      → Needs Fixes
Warnings only    → Review
All pass         → Review
QA inconclusive  → Blocked
```

QA report format:

```markdown
# QA Report — AE-xxxx

Status: PASS | WARN | FAIL | INCONCLUSIVE
Date: YYYY-MM-DD
QA Agent: qa-agent

## Summary

...

## Scope Reviewed

- Ticket: .agent/tasks/AE-xxxx-title.md
- Dev summary: .agent/reports/AE-xxxx.dev-summary.md
- Files reviewed:
  - ...

## Results

### 1. Security

Status: PASS | WARN | FAIL

Findings:
- ...

### 2. Code Quality

Status: PASS | WARN | FAIL

Findings:
- ...

### 3. Mutation / Edge Case Testing

Status: PASS | WARN | FAIL

Findings:
- ...

### 4. Acceptance Criteria Validation

Status: PASS | WARN | FAIL

Findings:
- ...

### 5. Orphan / Unfinished Code Detection

Status: PASS | WARN | FAIL

Findings:
- ...

## Required Fixes

- ...

## Recommended Follow-Ups

- ...

## Final QA Decision

PASS | WARN | FAIL | INCONCLUSIVE
```

---

### 5.7 Release Manager Agent

**Purpose:** Prepare completed work for human review, PR, merge, and release.

Responsibilities:

```text
- Verify QA report exists
- Verify docs and ADRs are updated
- Verify conventional commit messages
- Verify migration and rollback notes
- Verify PR description
- Prepare release summary
- Move ticket to Ready to Merge only if all required evidence exists
```

Restrictions:

```text
- Does not auto-merge
- Does not skip human review
- Does not mark Done without approval
```

Expected outputs:

```text
- PR description
- Release notes
- Final ticket summary
- Done checklist
```

---

### 5.8 Documentation / ADR Agent

This can be a separate skill or part of the Architect Agent.

Responsibilities:

```text
- Create ADRs for significant workflow decisions
- Update docs/guides
- Keep README references short
- Ensure docs follow repo conventions
```

---

## 6. Ticket Lifecycle

### 6.1 Statuses

Use the following status enum:

```text
Intake
Shaping
Ready
Planning
In Development
Dev Complete
QA Running
Needs Fixes
Blocked
Review
Ready to Merge
Done
Cancelled
```

### 6.2 Status Ownership

```text
Intake             → Human or Planner
Shaping            → Planner
Ready              → Ticket Writer
Planning           → Architect
In Development     → Developer Skill
Dev Complete       → Developer Skill
QA Running         → QA Agent
Needs Fixes        → QA Agent / Orchestrator
Blocked            → Orchestrator
Review             → Human
Ready to Merge     → Release Manager
Done               → Human / Release Manager
Cancelled          → Human / Orchestrator
```

### 6.3 Transition Guards

A ticket cannot move to `Ready` unless it has:

```text
- Goal
- Problem
- Scope
- Non-goals
- Acceptance criteria
- Affected areas
- Test strategy
- Dependencies
```

A ticket cannot move to `In Development` unless it has:

```text
- Approved implementation plan
- Branch/worktree name
- Clear likely affected files or modules
- QA checklist
```

A ticket cannot move to `Dev Complete` unless it has:

```text
- Acceptance criteria updated
- Files touched updated
- Test evidence added
- Developer summary written
```

A ticket cannot move to `Review` unless it has:

```text
- Dev summary
- QA report
- Known risks
- Files changed
- Test evidence
```

A ticket cannot move to `Ready to Merge` unless it has:

```text
- QA PASS or accepted WARN
- PR description
- Documentation updates, if needed
- ADR updates, if needed
- Migration/rollback notes, if needed
```

A ticket cannot move to `Done` unless it has:

```text
- Human approval
- Passing required checks
- Final summary
- Linked commit or PR
```

---

## 7. Canonical Ticket Template

Create this file:

```text
.agent/tasks/_template.md
```

Template:

```markdown
# AE-0000 — Ticket Title

Status: Intake
Priority: Medium
Type: Feature | Bug | Refactor | Docs | Test | CI | Platform | Architecture
Area: Backend | Frontend | Agent Workflow | Docs | Infrastructure | QA | Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: YYYY-MM-DD
Updated: YYYY-MM-DD

## Goal

Describe the outcome this ticket should produce.

## Problem

Describe the problem or opportunity.

## Scope

- ...

## Non-Goals

- ...

## Acceptance Criteria

- [ ] ...

## Gherkin Scenarios

```gherkin
Feature: ...

  Scenario: ...
    Given ...
    When ...
    Then ...
```

## Affected Areas

- Backend:
- Frontend:
- Database:
- API:
- Tests:
- Docs:
- Prompts/LLM:
- Observability:
- Deployment:

## Dependencies

- Blocks:
- Blocked by:
- Related:

## Implementation Plan

1. ...

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### YYYY-MM-DD HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
```

---

## 8. Board State File

Create:

```text
.agent/BOARD.md
```

Initial content:

```markdown
# Agentic Delivery Board

This file mirrors the visual Kanban board and acts as durable board state.

The visual board is for orchestration.
This file is the fallback source for agents.

## Intake

- None

## Shaping

- None

## Ready

- None

## Planning

- None

## In Development

- None

## Dev Complete

- None

## QA Running

- None

## Needs Fixes

- None

## Blocked

- None

## Review

- None

## Ready to Merge

- None

## Done

- None

## Cancelled

- None
```

---

## 9. Active Task File

Create:

```text
.agent/active-task.md
```

Initial content:

```markdown
# Active Task

Current active ticket: None

## Rules

- Only one ticket should be active per agent session unless explicitly coordinating multiple tickets.
- The active ticket must exist under `.agent/tasks/`.
- Agents must update the active ticket before and after implementation work.
- QA must clear active task ownership after writing its report.
```

---

## 10. Agent Configuration

Create:

```text
.agent/config.yaml
```

Initial content:

```yaml
project: alter-ego

ticket_prefix: AE

statuses:
  - Intake
  - Shaping
  - Ready
  - Planning
  - In Development
  - Dev Complete
  - QA Running
  - Needs Fixes
  - Blocked
  - Review
  - Ready to Merge
  - Done
  - Cancelled

wip_limits:
  Planning: 2
  In Development: 3
  QA Running: 2
  Review: 3

high_risk_areas:
  - authentication
  - authorization
  - database_migrations
  - langgraph_workflow_state
  - prompts
  - llm_provider_changes
  - publishing
  - scheduling
  - file_uploads
  - deployment

auto_commit:
  allowed:
    - docs
    - ticket_metadata
    - tests_only
  forbidden:
    - database_migrations
    - authentication
    - authorization
    - deployment
    - dependency_upgrades
    - prompt_behavior_changes

human_approval_required:
  - merge
  - release
  - high_risk_changes
  - security_sensitive_changes
```

---

## 11. Kanban Integration Strategy

### 11.1 Visual board

Use Cline Kanban or a similar tool as the visual board.

Recommended convention:

```text
One Kanban card = one .agent/tasks/AE-xxxx.md ticket = one branch/worktree
```

Card title:

```text
AE-0001 — Implement Agentic Delivery System
```

Card description:

```text
Path: .agent/tasks/AE-0001-agentic-delivery-system.md
Branch: feat/ae-0001-agentic-delivery
Agent lane: planner → architect → developer → qa → release
```

Labels:

```text
backend
frontend
docs
qa
adr
migration
feature-flag
agent-workflow
```

### 11.2 Worktree policy

```text
- Each card gets its own worktree.
- Each worktree gets its own branch.
- Branch name format: feat/ae-xxxx-short-title
- Agents should not work on the same source files in parallel unless explicitly coordinated.
```

### 11.3 Board synchronization

Add scripts to keep `.agent/BOARD.md` updated:

```text
scripts/agent_tasks/create_ticket.py
scripts/agent_tasks/move_ticket.py
scripts/agent_tasks/validate_ticket.py
scripts/agent_tasks/render_board.py
scripts/agent_tasks/summarize_ticket.py
```

Example commands:

```bash
uv run python scripts/agent_tasks/create_ticket.py \
  --title "Add ticket schema" \
  --type platform \
  --area agent-workflow

uv run python scripts/agent_tasks/move_ticket.py AE-0001 --status "In Development"

uv run python scripts/agent_tasks/validate_ticket.py AE-0001

uv run python scripts/agent_tasks/render_board.py
```

---

## 12. Required Skills to Add

### 12.1 `skills/planner-skill/SKILL.md`

```markdown
# Planner Skill

## Purpose

Break fuzzy product or technical requests into epics, tickets, dependencies, and risks.

## Rules

- Do not write code.
- Do not modify production source files.
- Do not mark tickets Ready without acceptance criteria.
- Always identify backend, frontend, docs, tests, migrations, and feature flag impact.
- Split work so one ticket can be completed by one agent in one branch.
- Prefer vertical slices when possible.
- Add dependencies explicitly.

## Required Inputs

- User request or product goal
- Current project context
- Existing `.agent/BOARD.md`
- Existing tickets under `.agent/tasks/`

## Required Output

- Epic summary
- Ticket list
- Dependencies
- Risks
- Suggested implementation order
- Handoff to Architect Agent
```

---

### 12.2 `skills/architect-skill/SKILL.md`

```markdown
# Architect Skill

## Purpose

Validate the technical approach before implementation.

## Rules

- Read root `CLAUDE.md`.
- Read local `CLAUDE.md` and `AGENTS.md` files for relevant areas.
- Check `docs/decisions/` before making architectural recommendations.
- Create or recommend an ADR for architecturally significant changes.
- Define API contracts before dependent frontend/backend work starts.
- Define migration and rollback strategy when data changes.
- Define testing strategy.
- Do not write production code unless explicitly switched into Developer role.

## Required Inputs

- Ticket file
- Planner output
- Current architecture docs
- Relevant AGENTS.md / CLAUDE.md files

## Required Output

- Technical plan
- Affected modules
- API contracts
- Data model changes
- ADR required: yes/no
- Testing strategy
- Rollout strategy
- Handoff to Ticket Writer or Developer
```

---

### 12.3 `skills/ticket-writer-skill/SKILL.md`

```markdown
# Ticket Writer Skill

## Purpose

Convert plans and architectural notes into properly scoped `.agent/tasks/AE-xxxx.md` ticket files.

## Rules

- Every ticket must have acceptance criteria.
- Every ticket must have scope and non-goals.
- Every behavior-changing ticket must include Gherkin scenarios.
- Every ticket must include a QA checklist.
- Every ticket must identify dependencies.
- Do not write production code.
- Do not mark tickets Ready if required fields are missing.

## Required Inputs

- Planner output
- Architect output, if available
- Existing ticket template

## Required Output

- New or updated `.agent/tasks/AE-xxxx-title.md`
- Updated `.agent/BOARD.md`
- Handoff to Developer or Orchestrator
```

---

### 12.4 `skills/orchestrator-skill/SKILL.md`

```markdown
# Orchestrator Skill

## Purpose

Manage the agentic workflow across ticket states, board state, handoffs, and WIP limits.

## Rules

- Keep exactly one owner per ticket at a time.
- Never assign overlapping file changes to parallel agents unless explicitly coordinated.
- Keep `.agent/BOARD.md` synchronized.
- Move tickets only when transition guards are satisfied.
- Route work to Planner, Architect, Ticket Writer, Developer, QA, or Release Manager.
- Detect and document blockers.
- Do not implement production code.

## Required Inputs

- `.agent/BOARD.md`
- `.agent/config.yaml`
- Relevant ticket files
- Agent reports

## Required Output

- Updated ticket status
- Updated `.agent/BOARD.md`
- Handoff notes
- Blocker notes
```

---

### 12.5 `skills/release-manager-skill/SKILL.md`

```markdown
# Release Manager Skill

## Purpose

Prepare completed work for human review, PR, merge, and release.

## Rules

- Do not auto-merge.
- Verify QA report exists.
- Verify docs and ADRs are updated when required.
- Verify conventional commit messages.
- Verify migration and rollback notes when required.
- Create final ticket summary.
- Move ticket to Ready to Merge only when all evidence exists.
- Move ticket to Done only after human approval.

## Required Inputs

- Ticket file
- Developer summary
- QA report
- Git diff
- Test evidence
- Docs/ADR changes, if any

## Required Output

- PR description
- Release notes
- Final ticket summary
- Done checklist
```

---

## 13. Updates to Existing Skills

### 13.1 Update `developer-skill`

Add this section:

```markdown
## Agentic Ticket Protocol

Before coding:

1. Read `.agent/active-task.md`.
2. Read the active ticket under `.agent/tasks/`.
3. Verify the ticket has acceptance criteria and an implementation plan.
4. Move the ticket to `In Development`.
5. Add a timestamped entry to `Progress Log`.
6. Record the branch/worktree.

During coding:

1. Implement one acceptance criterion at a time.
2. Update the ticket `Progress Log` after each meaningful milestone.
3. Update `Files Touched`.
4. Update `Test Evidence` after each verification run.
5. Do not mark an acceptance criterion complete until implementation and tests exist.

After coding:

1. Move the ticket to `Dev Complete`.
2. Write `.agent/reports/AE-xxxx.dev-summary.md`.
3. Update `.agent/BOARD.md`.
4. Handoff to QA Agent.
```

---

### 13.2 Update `qa-agent`

Add this section:

```markdown
## Agentic Ticket QA Protocol

Before QA:

1. Read the ticket under `.agent/tasks/`.
2. Read the developer summary under `.agent/reports/`.
3. Move the ticket to `QA Running`.
4. Identify changed files and acceptance criteria.

During QA:

1. Run the existing QA dimensions.
2. Store evidence for each dimension.
3. Link findings to file paths and line numbers when possible.

After QA:

1. Write `.agent/reports/AE-xxxx.qa.md`.
2. Update the ticket `QA Report` section.
3. Move the ticket based on result:
   - Blockers found → `Needs Fixes`
   - Warnings only → `Review`
   - All pass → `Review`
   - Inconclusive → `Blocked`
4. Update `.agent/BOARD.md`.
```

---

## 14. Handoff Protocols

### 14.1 Planner → Architect

```markdown
## Handoff to Architect

Ticket/Epic: AE-xxxx
Problem: ...
Proposed scope: ...
Risks: ...
Open decisions: ...
Recommended next step: validate architecture and create ADR if needed.
```

### 14.2 Architect → Ticket Writer

```markdown
## Handoff to Ticket Writer

Architecture summary: ...
Affected modules: ...
API contracts: ...
Data model impact: ...
ADR required: yes/no
Testing strategy: ...
```

### 14.3 Ticket Writer → Developer

```markdown
## Handoff to Developer

Ticket: AE-xxxx
Status: Ready
Acceptance criteria: ...
Suggested order: ...
Commands to run: ...
Known risks: ...
```

### 14.4 Developer → QA

```markdown
## Handoff to QA

Ticket: AE-xxxx
Status: Dev Complete
Files changed: ...
Tests run: ...
Known risks: ...
Dev summary: .agent/reports/AE-xxxx.dev-summary.md
```

### 14.5 QA → Human Review

```markdown
## Handoff to Human Review

Ticket: AE-xxxx
QA status: PASS/WARN/FAIL
QA report: .agent/reports/AE-xxxx.qa.md
Top risks: ...
Recommended action: approve / request fixes / block merge
```

---

## 15. WIP and Concurrency Rules

Because visual Kanban tools can run multiple tasks in parallel, enforce these rules:

```text
Rule 1: One ticket owns one worktree.
Rule 2: One worktree owns one branch.
Rule 3: Two agents cannot modify the same file family without explicit dependency.
Rule 4: Shared API contracts are implemented before dependent frontend/backend tasks.
Rule 5: Database migrations are never parallelized with dependent repository/service changes unless sequenced.
Rule 6: QA is read-only.
Rule 7: Release Manager cannot merge without human approval.
```

Recommended default WIP limits:

```text
Planning: 2
In Development: 3
QA Running: 2
Review: 3
```

For a solo operator, start with:

```text
In Development: 1 backend + 1 frontend + 1 docs/tooling
QA Running: 1
```

---

## 16. Safety and Quality Controls

### 16.1 No autonomous merge

Agents may prepare commits or PRs, but must not auto-merge.

### 16.2 Auto-commit policy

Allowed:

```text
- Docs-only tickets
- Ticket metadata updates
- Small tests-only changes
```

Forbidden:

```text
- Database migrations
- Auth/security changes
- Deployment changes
- Dependency upgrades
- Prompt/model behavior changes
```

### 16.3 Required QA for high-risk areas

Always require QA for:

```text
- Authentication
- Authorization
- Database migrations
- LangGraph workflow state
- Prompt changes
- LLM provider changes
- Publishing/scheduling
- File uploads
- Deployment changes
```

---

## 17. CI and Validation

Add a lightweight CI job that validates agent ticket hygiene.

Checks:

```text
- Every ticket has required fields
- Every Ready/In Development ticket has acceptance criteria
- Every Dev Complete ticket has test evidence
- Every Review ticket has QA report
- Every Done ticket has final summary and PR/commit link
- No ticket has an invalid status
- No ticket is stuck In Development beyond the configured threshold without progress update
```

Suggested command:

```bash
uv run python scripts/agent_tasks/validate_all_tickets.py
```

Example validation errors:

```text
AE-0003: Missing acceptance criteria
AE-0004: Status is Review but no QA report is linked
AE-0005: Done ticket missing final summary
AE-0006: In Development for 5 days with no progress log update
```

---

## 18. Initial Implementation Backlog

### AE-0001 — Document the Agentic Delivery System

Type: Docs
Owner: Architect Agent
Status: Ready

Acceptance criteria:

```text
- [ ] Add docs/plans/agentic-delivery-system.md
- [ ] Add docs/guides/agentic-team-operating-model.md
- [ ] Document ticket lifecycle
- [ ] Document Kanban usage
- [ ] Document DEV → QA loop
- [ ] Document human approval gates
```

---

### AE-0002 — Add ADR for Agentic Delivery Workflow

Type: Architecture
Owner: Architect Agent
Status: Ready

Acceptance criteria:

```text
- [ ] Add docs/decisions/0008-agentic-delivery-workflow.md
- [ ] Decision explains why board UI and repo-backed tickets are separated
- [ ] Decision explains why Kanban is orchestration, not canonical state
- [ ] Decision defines human review as final merge gate
- [ ] Decision documents risks of autonomous auto-commit/auto-PR
```

---

### AE-0003 — Add Canonical Ticket Schema

Type: Platform
Owner: Ticket Writer Agent
Status: Ready

Acceptance criteria:

```text
- [ ] Add .agent/tasks/_template.md
- [ ] Add required field list
- [ ] Add status enum
- [ ] Add priority enum
- [ ] Add ticket type enum
- [ ] Add Gherkin section
- [ ] Add QA report link section
```

---

### AE-0004 — Add Board State File

Type: Platform
Owner: Orchestrator Agent
Status: Ready

Acceptance criteria:

```text
- [ ] Add .agent/BOARD.md
- [ ] Board includes all lifecycle columns
- [ ] Board references ticket IDs
- [ ] Board explains that visual Kanban is the UI and BOARD.md is durable state
```

---

### AE-0005 — Add Planner Skill

Type: Skill
Owner: Developer Skill
Status: Ready

Acceptance criteria:

```text
- [ ] Add skills/planner-skill/SKILL.md
- [ ] Planner cannot write code
- [ ] Planner produces epics, tickets, dependencies, and risks
- [ ] Planner outputs ticket-ready acceptance criteria
```

---

### AE-0006 — Add Architect Skill

Type: Skill
Owner: Developer Skill
Status: Ready

Acceptance criteria:

```text
- [ ] Add skills/architect-skill/SKILL.md
- [ ] Architect reads CLAUDE.md and AGENTS.md
- [ ] Architect checks ADR impact
- [ ] Architect defines implementation approach
- [ ] Architect marks whether ADR is required
```

---

### AE-0007 — Add Ticket Writer Skill

Type: Skill
Owner: Developer Skill
Status: Ready

Acceptance criteria:

```text
- [ ] Add skills/ticket-writer-skill/SKILL.md
- [ ] Skill writes ticket files from plans
- [ ] Skill validates acceptance criteria
- [ ] Skill adds Gherkin scenarios when behavior changes
- [ ] Skill adds QA checklist
```

---

### AE-0008 — Add Orchestrator Skill

Type: Skill
Owner: Developer Skill
Status: Ready

Acceptance criteria:

```text
- [ ] Add skills/orchestrator-skill/SKILL.md
- [ ] Skill owns status transitions
- [ ] Skill updates BOARD.md
- [ ] Skill routes to Planner, Architect, Developer, QA, and Release Manager
- [ ] Skill enforces WIP limits
```

---

### AE-0009 — Add Release Manager Skill

Type: Skill
Owner: Developer Skill
Status: Ready

Acceptance criteria:

```text
- [ ] Add skills/release-manager-skill/SKILL.md
- [ ] Skill verifies QA report
- [ ] Skill verifies docs/ADR updates
- [ ] Skill prepares PR description
- [ ] Skill prepares release summary
- [ ] Skill does not auto-merge
```

---

### AE-0010 — Update Developer Skill for Ticket Progress

Type: Skill Enhancement
Owner: Developer Skill
Status: Ready

Acceptance criteria:

```text
- [ ] Developer Skill reads active ticket file
- [ ] Developer Skill moves status to In Development
- [ ] Developer Skill updates progress log
- [ ] Developer Skill updates files touched
- [ ] Developer Skill records tests run
- [ ] Developer Skill writes dev summary report
```

---

### AE-0011 — Update QA Agent for Persistent Reports

Type: Skill Enhancement
Owner: Developer Skill
Status: Ready

Acceptance criteria:

```text
- [ ] QA Agent reads ticket file
- [ ] QA Agent reads dev summary
- [ ] QA Agent writes .agent/reports/AE-xxxx.qa.md
- [ ] QA Agent updates ticket status based on findings
- [ ] QA Agent links blocker findings back to ticket
```

---

### AE-0012 — Add Ticket Validation Scripts

Type: Tooling
Owner: Developer Skill
Status: Ready

Acceptance criteria:

```text
- [ ] Add create_ticket script
- [ ] Add move_ticket script
- [ ] Add validate_ticket script
- [ ] Add render_board script
- [ ] Add validate_all_tickets script
- [ ] Scripts are tested
```

---

### AE-0013 — Add CI Guard for Agentic Tickets

Type: CI
Owner: Developer Skill
Status: Ready

Acceptance criteria:

```text
- [ ] CI validates ticket schema
- [ ] CI fails if Review ticket has no QA report
- [ ] CI warns if stale In Development ticket exists
- [ ] CI checks no ticket has invalid status
```

---

### AE-0014 — Configure Kanban Usage Guide

Type: Docs/Tooling
Owner: Release Manager Agent
Status: Ready

Acceptance criteria:

```text
- [ ] Add docs/guides/kanban-agent-workflow.md
- [ ] Explain how to run the visual Kanban board
- [ ] Explain card naming convention
- [ ] Explain one card = one ticket = one worktree
- [ ] Explain when auto-commit is allowed
- [ ] Explain human review rules
```

---

## 19. Recommended Implementation Order

```text
1. Add ADR and docs plan
2. Add ticket template
3. Add BOARD.md
4. Add planner-skill
5. Add architect-skill
6. Add ticket-writer-skill
7. Add orchestrator-skill
8. Update developer-skill
9. Update qa-agent
10. Add validation scripts
11. Add CI guard
12. Add Kanban usage guide
13. Run a pilot ticket end-to-end
```

---

## 20. First Milestone

The first milestone should be:

```text
Milestone 1: Persistent Agentic Ticketing
```

Deliverables:

```text
- .agent/BOARD.md
- .agent/tasks/_template.md
- docs/plans/agentic-delivery-system.md
- docs/decisions/0008-agentic-delivery-workflow.md
- skills/planner-skill/SKILL.md
- skills/orchestrator-skill/SKILL.md
- skills/release-manager-skill/SKILL.md
- Updated developer-skill
- Updated qa-agent
```

Then use the visual Kanban board on top of that.

---

## 21. Pilot Ticket Recommendation

The first real ticket should be low risk and docs/tooling-only.

Recommended pilot:

```text
AE-0015 — Add ticket validation script for required fields
```

Purpose:

```text
Validate the full agentic workflow before using it for backend/frontend features.
```

Acceptance criteria:

```text
- [ ] Script scans `.agent/tasks/*.md`
- [ ] Script validates required fields
- [ ] Script validates status enum
- [ ] Script validates Review tickets have QA reports
- [ ] Script prints actionable errors
- [ ] Script exits non-zero on blocking validation failures
- [ ] Script has tests or documented test evidence
```

---

## 22. Implementation Instructions for Coding Agent

When implementing this plan, follow this sequence:

```text
1. Read root CLAUDE.md.
2. Read relevant AGENTS.md files.
3. Inspect existing skills under skills/.
4. Create `.agent/` structure.
5. Add ticket template.
6. Add board file.
7. Add docs plan and ADR.
8. Add new skills.
9. Update existing developer and QA skills.
10. Add scripts.
11. Add validation tests.
12. Run available checks.
13. Write developer summary.
14. Run QA agent.
15. Prepare final review summary.
```

Implementation must preserve existing project conventions and avoid disrupting existing DEV/QA workflows.

---

## 23. Final Target Operating Model

```text
Cline Kanban or similar visual board
  = visual execution board

.agent/tasks/*.md
  = durable ticket memory

.agent/reports/*.md
  = DEV and QA evidence

docs/plans/*.md
  = formal plans

docs/decisions/*.md
  = architectural decisions

skills/*
  = agent roles and behavior contracts

Git branches/worktrees
  = isolated implementation spaces

Human review
  = final approval gate
```

This turns the existing DEV → QA loop into a complete agentic delivery system with visible board progress and durable traceability.
