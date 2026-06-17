# AE-0170 — Worktree isolation + HEAD-detach guard for external QA/kaizen runs

Status: Intake
Tier: T2
Class: B
Priority: High
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Run external QA/kaizen CLIs in an isolated git worktree with a HEAD-detach guard so a non-sandboxed tool can never mutate the working branch or strand commits. Source: kaizen sweep `.agent/reports/kaizen-sweep-2026-06-16.plan.md` P5.

## Problem

External (cursor/opencode) QA tooling is non-sandboxed: it has created rogue files, gutted `run_external_qa.sh`, and DETACHED HEAD so commits landed off-branch (recovered via reflog). Combined with `--no-verify`/partial staging this caused a lost-commit incident (see MEMORY: `no-git-add-all-with-uncommitted-work`). `scripts/lib/external_agent.sh` has process hardening but no git-state isolation.

## Scope

- Run external CLIs inside a dedicated `git worktree` (separate checkout) so they cannot touch the primary working tree/branch.
- Add a HEAD-detach / branch-moved guard that aborts + restores if the external run leaves the repo in an unexpected git state; assert `git status -sb` + current branch before/after.
- Keep only the external run's `/tmp` structured output as authoritative (already the convention); auto-clean the worktree.

## Non-Goals

- Not removing external offload (it saves tokens); harden it.
- Not weakening any QA/kaizen gate.

## Acceptance Criteria

- [ ] External QA/kaizen runs execute in an isolated worktree; the primary branch HEAD + working tree are provably unchanged after a run.
- [ ] A HEAD-detach or branch-move by the external tool is detected and the run aborts with the repo restored (verified on a SEEDED detach/rogue-write).
- [ ] `run_external_qa.sh` / `run_external_kaizen.sh` still produce valid `/tmp` output; worktree auto-cleaned.

## Gherkin Scenarios

```gherkin
Feature: ...

  Scenario: ...
    Given ...
    When ...
    Then ...
```

## Delta

### ADDED

- ...

### MODIFIED

- ...

### REMOVED

- ...

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

### 2026-06-16 HH:mm

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
