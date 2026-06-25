# AE-0282 — visual and cross-layer verification doc ratchet

Status: Intake
Tier: T1
Priority: P3
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Branch: TBD
Created: 2026-06-25
Updated: 2026-06-25

## Goal

Codify two verification rules — proven by repeated go-live incidents — as written
project standards so the next session can't skip them: (1) shell/layout/responsive
work requires Playwright-MCP rendering verification at real viewports before Dev
Complete; (2) a frontend change that sends a NEW value shape to an EXISTING
backend endpoint requires an integration test exercising the real contract.

## Problem

(Kaizen failure classes C1 + C2 — the process half; the mechanical half is the
P1/P2 lint gates, AE-0279/0280.)

Two go-live blockers shipped because gates compile but never RENDER, and
per-scope gates never exercise the FE→BE path:

- **C1 (AE-0272 epic):** 4 runtime-only CSS bugs (z-index stacking trap, `@theme`
  tree-shake, missing `min-w-0`, duplicate icon) all compiled clean and passed all
  17 gates; the user caught them post-deploy at real viewports (PRs #68, #69).
- **C2 (AE-0271):** the create dropdown sent a 36-char UUID theme to a backend
  route that capped theme at 30 chars + forced a root-enum → 422/500. Frontend
  gates green (valid FE) + backend gates green (no backend file in the FE view) →
  the cross-layer path was never exercised. External QA caught it as a GO-LIVE
  BLOCKER.

Both are documented in memories (`external-qa-catches-drawer-correctness`,
`cross-layer-validation-gap`) but those are recall hints, not enforced rules — a
fresh session is not bound by them.

Note (honest framing): this is a DOC/process ratchet, not a mechanical gate, so
its strength depends on being honored. It pairs with the mechanical gates
(AE-0279 catches the `@theme` face of C1). Where a rule here can later be made
mechanical, prefer promoting it.

Source: `.agent/reports/kaizen-session-2026-06-25.plan.md` (proposal P5),
learnings records 10 & 11.

## Scope

- Add to `frontend/AGENTS.md` + `CLAUDE.md` + `docs/guides/qa-checkpoints.md`:
  - **Visual-verification rule:** any ticket touching the app shell, layout,
    responsive behavior, stacking, or overflow MUST verify the rendered result
    via Playwright MCP at **390** and **1440** viewports (backend up + local
    admin login) before Dev Complete. List the known render-invisible traps:
    `@theme` tree-shake, `min-w-0`-on-flex-ancestor, nested z-index context,
    Playwright stale-CSS cache (re-inject `<link>?cb=` before measuring).
  - **Cross-layer-contract rule:** any FE change that sends a NEW value shape /
    length / type to an EXISTING backend endpoint MUST ship an integration test
    that drives the real contract (e.g. direct ASGI / API call), since per-scope
    gates won't exercise it.
- Cross-link the two memories so the rules and the recall hints reinforce.

## Non-Goals

- Do not refactor unrelated code.
- No new mechanical gate here (that's AE-0279/AE-0280); this is the doc/process
  ratchet.
- Don't mandate Playwright for non-visual tickets (avoid blanket friction).

## Acceptance Criteria

- [ ] `frontend/AGENTS.md`, `CLAUDE.md`, and `docs/guides/qa-checkpoints.md` state
      the visual-verification rule (390 + 1440, the named traps) and the
      cross-layer-contract rule (integration test for new value shapes to existing
      endpoints), as Dev-Complete preconditions for the relevant ticket classes.
- [ ] The qa-checkpoints entry is concrete enough that QA can mark it
      pass/fail (names the viewports + the "new value shape to existing endpoint"
      trigger).
- [ ] Memories `external-qa-catches-drawer-correctness` and
      `cross-layer-validation-gap` are cross-linked from the new rules.

## Repro Steps

1. (Reference) AE-0272 PRs #68/#69 and AE-0271 — both green on all gates, both
   broke at runtime / across the FE→BE boundary; caught only by humans / external
   QA at real viewports.

## Affected Areas

- [x] Frontend (AGENTS.md, qa-checkpoints)
- [x] Tests (cross-layer integration-test expectation)
- Docs: CLAUDE.md, frontend/AGENTS.md, docs/guides/qa-checkpoints.md

## Dependencies

- Related: AE-0279 (mechanical `@theme` gate — C1), AE-0280 (migration gate),
  AE-0277 (responsive gate), memories `external-qa-catches-drawer-correctness`,
  `cross-layer-validation-gap`.

## Progress Log

### 2026-06-25 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
