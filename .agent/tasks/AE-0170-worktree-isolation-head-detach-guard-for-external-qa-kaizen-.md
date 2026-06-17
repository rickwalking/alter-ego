# AE-0170 — Worktree isolation + HEAD-detach guard for external QA/kaizen runs

Status: Done
Tier: T2
Class: B
Priority: High
Type: Quality
Area: Cross-cutting
Owner: developer-skill
Agent Lane: planner → architect → developer → qa → release
Branch: chore/phase-8-class-b
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

- [x] External QA/kaizen runs execute in an isolated worktree; the primary branch HEAD + working tree are provably unchanged after a run. Added `ext_run_guarded()` to `scripts/lib/external_agent.sh` (throwaway DETACHED worktree; CLI runs with cwd/repo-root = worktree).
- [x] A HEAD-detach or branch-move by the external tool is detected and the run aborts (rc 4) with the repo restored — verified on a SEEDED detach (`scripts/lib/external_agent_guard_check.sh` + `frontend/src/scripts/external-guard.test.ts`).
- [x] `run_external_qa.sh` / `run_external_kaizen.sh` now call `ext_run_guarded`; `/tmp` `<output-file>` stays authoritative; worktree auto-cleaned (`--force` + prune).

## Test Evidence

`bash scripts/lib/external_agent_guard_check.sh` → "guard-check OK" (clean run: rc 0,
primary unchanged, worktree cleaned; rogue detach: rc 4, restored to main@HEAD0,
worktree cleaned). `npx vitest run src/scripts/external-guard.test.ts` → 1 passed.
Uses temp repos — the working repo is never touched.

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

Worktree isolation + HEAD-detach guard implemented in scripts/lib/external_agent.sh for external QA/kaizen runs. Verified in main.
