# AE-0152 — Frontend dead-export / unused-code gate (knip, baseline-ratchet)

Status: Intake
Tier: T2
Priority: High
Type: Quality
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

A frontend dead-export / unused-code detector (knip), wired into the
single-source-of-truth runner as a **baseline-ratchet** gate (advisory first,
then blocking), so net-new orphaned exports/files are caught automatically.

## Problem

Source: kaizen `.agent/reports/kaizen-AE-0149-0151.plan.md` (failure class #1).
The frontend has **no** unused-export/dead-code detector. ESLint
`no-unused-vars` sees unused locals/imports but never cross-file *exports*. The
backend has `vulture` (`scripts/ci/gates.sh` `gate_backend_dead_code`); the
frontend has no equivalent — an asymmetry. In AE-0150, `MESSAGE_ROLE_USER` /
`MESSAGE_ROLE_ASSISTANT` in `frontend/src/constants/publish-chat.ts` became
production-orphaned after a refactor and were caught **manually by QA**, not by
any gate.

Research (kaizen): **knip** is the 2025/2026 standard (ts-prune archived → knip;
`eslint import/no-unused-modules` false-positives on `@/*` absolute imports + the
29 barrel files and bloats lint time). knip's Next.js plugin understands
app-router entrypoints (`page/layout/route.tsx`), so it won't flag framework
files. A first run will surface dozens–100+ findings (barrel re-exports,
public-API constants, shared types) → must grandfather a baseline and ratchet
DOWN, exactly like the jscpd threshold and the component-type baseline.

## Scope

- Add `knip` devDependency + `frontend/knip.json` (Next.js + Storybook + Vitest
  entrypoints; `exports`/`files` as `warn`).
- `frontend/scripts/check-dead-code.mjs` + `generate-dead-code-baseline.mjs` +
  `dead-code-baseline.json` — reuse the `check-component-type-location.mjs`
  baseline-ratchet pattern (grandfather current count + allowlist; block only
  NET-NEW; DOWN-only). Scripts: `lint:dead-code`, `dead-code:baseline`.
- `gate_frontend_dead_code` in `scripts/ci/gates.sh` + register `dead-code` in
  `FRONTEND_GATES`; `frontend / Dead code` CI job, **advisory
  (`continue-on-error: true`) for the introductory wave** (mirror jscpd
  test-advisory / mutation), flip to blocking in a follow-up.
- Register the baseline in `scripts/ci/check-integrity.sh` so a raised count is
  flagged as loosening (like `BASELINE_*` / jscpd `"threshold"`).
- Document in `frontend/AGENTS.md` + `docs/guides/qa-checkpoints.md`.

## Non-Goals

- Removing all currently-grandfathered dead code (separate refactor tickets).
- Per-file coverage gate or zero-tolerance (would be too noisy on barrels/public API).

## Acceptance Criteria

- [ ] `bash scripts/ci/gates.sh frontend:dead-code` passes at the grandfathered baseline.
- [ ] **Baseline is keyed by finding IDENTITY, not total count** — each grandfathered
      entry is `{rule, file, symbol}` (not just a number). A replace-same-count
      churn (remove one old unused export, add one new) is REJECTED. (Skeptical
      review BLOCKER.) Tests must cover add / remove / replace-same-count / rename /
      allowlist-scope.
- [ ] **Net-new findings in PR-changed files BLOCK from day one**; the full-tree
      sweep stays advisory only for pre-existing grandfathered debt. (Avoids the
      "advisory normalizes drift" gap — fresh dead code cannot merge while the gate
      is "advisory".)
- [ ] **The gate FAILS on a seeded net-new unused export** (prove enforcement).
- [ ] Next.js/Storybook/Vitest entrypoints are NOT false-flagged.
- [ ] The grandfathered baseline set can only **shrink** (re-adding a removed
      identity or raising the count is flagged by `check-integrity.sh`).
- [ ] Gate runs in CI and is documented in AGENTS.md + qa-checkpoints, including an
      **operating-model note**: runtime budget (target seconds added to CI), gate
      owner, and the explicit event that flips the full-tree sweep from advisory to
      blocking (e.g. "grandfathered count reaches 0", or a dated deadline).

## Gherkin Scenarios

```gherkin
Feature: Frontend dead-export gate

  Scenario: A new unused export above the baseline is rejected
    Given the committed dead-code baseline
    When a change adds an exported symbol that nothing imports
    Then "scripts/ci/gates.sh frontend:dead-code" fails

  Scenario: Framework entrypoints are not flagged
    Given knip is configured with the Next.js/Storybook/Vitest plugins
    When the gate runs over app-router page/layout/route files
    Then they are treated as entrypoints, not dead code

  Scenario: The baseline may only ratchet down
    Given a committed dead-code baseline count of N
    When a change raises the baseline above N
    Then check-integrity flags it as gate-loosening
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
- Related: AE-0149 (jscpd gate — same baseline-ratchet + single-source-of-truth
  pattern to reuse), AE-0150 (the refactor whose orphaned constants motivated this).
  Source: `.agent/reports/kaizen-AE-0149-0151.plan.md` (P1).
- **Blocked by: AE-0154** — the duplication refactor moves exports / creates shared
  primitives / changes barrel behavior, which churns knip results. Run AE-0154
  first, THEN snapshot the knip baseline, so the baseline doesn't immediately go
  stale. (Skeptical-review sequencing finding; the changed-file-only blocking above
  also makes AE-0152 robust to that churn.)

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

- 2026-06-16 — Skeptical review (`.agent/reports/AE-0152-0155.skeptical-review.md`,
  external cold critic): **BLOCKER accepted** — baseline keyed by `{rule,file,symbol}`
  identity, not count (replace-same-count must fail); ACs updated. **WARN accepted** —
  changed-file findings block from day one (full-tree sweep advisory until flip);
  added operating-model AC (runtime budget, owner, flip criterion). **WARN accepted** —
  sequenced after AE-0154 to avoid baseline churn.

## Blockers

None.

## Final Summary

Pending.
