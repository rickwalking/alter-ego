# AE-0279 — tailwind @theme tree-shake lint gate

Status: Intake
Tier: T2
Priority: P2
Type: Quality
Area: frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-25
Updated: 2026-06-25

## Goal

A static gate that fails CI when a Tailwind v4 `@theme {}` custom property is
referenced ONLY inside arbitrary-value utilities (`w-[var(--x)]`,
`shadow-[var(--x)]`, `border-[color:var(--x)]`, …) and never as a real Tailwind
token. Tailwind v4 tree-shakes such vars out of the emitted CSS, so the
arbitrary value resolves to an EMPTY custom property at build — silently
breaking layout/styling while every existing gate stays green.

## Problem

(Kaizen failure class C1 — render-invisible CSS bugs.)
The AE-0272 responsive-dashboard epic shipped a go-live blocker: `--sidebar-width`
was declared in `@theme{}` and used as `w-[var(--sidebar-width)]`. Tailwind v4
dropped the declaration (an arbitrary value is not a theme "use"), the var
resolved empty, and the sidebar got `width:auto` + content `margin-left:0` → page
content underlapped the rail on EVERY desktop dashboard page. It compiled clean
and was invisible to all 17 gates; the user caught it post-deploy (PR #69).

This is not hypothetical going forward — a live audit (2026-06-25) found **5
`@theme` vars already at this exact risk** in `frontend/src/app/globals.css`,
each referenced only inside arbitrary values:
`--shadow-neon-button`, `--shadow-neon-button-hover`, `--shadow-neon-card-hover`,
`--shadow-neon-danger`, `--color-neon-cyan-teal-end` (and `--color-neon-cyan-border-30`).

No ESLint rule or `frontend/scripts/check-*.mjs` gate detects this today
(`check-responsive-dashboard.mjs` only scans inline `style={{}}`; nothing inspects
class strings vs `@theme` declarations).

Source: `.agent/reports/kaizen-session-2026-06-25.plan.md` (proposal P1),
learnings record 11 (`.agent/handoff/learnings-log.jsonl`), memory
`external-qa-catches-drawer-correctness`.

## Scope

- New `frontend/scripts/check-theme-var-usage.mjs`, mirroring the existing
  `check-responsive-dashboard.mjs` / `check-palette-drift.mjs` convention
  (exit non-zero + actionable message on violation; exits 0 on the current tree
  once existing risks are resolved).
- Parse `@theme {}` block(s) in `frontend/src/app/globals.css` for declared
  `--vars`; scan `src/**/*.{ts,tsx,css}` for every `var(--x)` reference and for
  real Tailwind token usages; flag any declared var whose ONLY references are
  inside arbitrary-value utilities.
- Wire into `npm run lint` (the full chain CI runs) and register in
  `scripts/ci/gates.sh` frontend gates.
- Rule-fires regression test (AE-0180): seed a `@theme` var used only in an
  arbitrary value → assert the gate exits non-zero.
- Resolve the 5–6 pre-existing live violations (move each var out of `@theme`
  into `:root{}`/literal, or add a real token use) so the gate is green on HEAD.

## Non-Goals

- Detecting `min-w-0`-on-flex-ancestor overflow or z-index stacking traps (C1's
  other faces) — those are harder to lint reliably; covered by the P5 doc ratchet
  (AE-0282), not here.
- Changing the Neon design system's visual output (the var relocations must be
  byte-identical in rendered CSS).

## Acceptance Criteria

- [ ] `frontend/scripts/check-theme-var-usage.mjs` exists and is invoked by
      `npm run lint` and `scripts/ci/gates.sh frontend`.
- [ ] The gate FAILS (non-zero exit) on a seeded `@theme` var referenced only
      inside an arbitrary-value utility — proven by a rule-fires test
      (`check-theme-var-usage.test.ts`), per AE-0180. (Passing on the real tree
      proves nothing.)
- [ ] The 5–6 currently-at-risk vars in `globals.css` are resolved and the gate
      exits 0 on HEAD with rendered CSS unchanged.
- [ ] `docs/guides/qa-checkpoints.md` documents the new gate.

## Gherkin Scenarios

```gherkin
Feature: @theme var tree-shake gate

  Scenario: a var used only in an arbitrary value is flagged
    Given a custom property "--danger" declared inside a @theme block
    And it is referenced only as shadow-[var(--danger)] in a component
    When check-theme-var-usage runs
    Then it exits non-zero and names "--danger" as tree-shake-risky

  Scenario: a var used as a real Tailwind token passes
    Given "--color-primary-500" declared in @theme
    And it is used as the class "text-primary-500"
    When check-theme-var-usage runs
    Then it does not flag "--color-primary-500"

  Scenario: clean tree passes
    Given the current frontend tree after the at-risk vars are resolved
    When check-theme-var-usage runs
    Then it exits 0
```

## Delta

### ADDED

- `frontend/scripts/check-theme-var-usage.mjs`
- `frontend/scripts/check-theme-var-usage.test.ts` (rule-fires)

### MODIFIED

- `frontend/package.json` (lint chain)
- `scripts/ci/gates.sh` (register frontend gate)
- `frontend/src/app/globals.css` (relocate at-risk vars out of `@theme`)
- consumers of the relocated vars (neon-button.tsx, neon-card.tsx, …)
- `docs/guides/qa-checkpoints.md`

### REMOVED

- (none)

## Affected Areas

- Backend: none
- Frontend: globals.css `@theme` vars + the components consuming them
- Database: none
- API: none
- Tests: rule-fires test + token-sync style assertions
- Docs: qa-checkpoints.md
- Prompts/LLM: none
- Observability: none
- Deployment: none (gate runs in CI)

## Dependencies

- Blocks:
- Blocked by:
- Related: AE-0277 (check-responsive-dashboard gate — same convention), AE-0282
  (visual/cross-layer doc ratchet — C1 process half)

## Implementation Plan

1. Read `globals.css` `@theme` block; enumerate declared `--vars`.
2. Write the checker: build the set of declared theme vars, the set referenced
   via real Tailwind tokens, and the set referenced only via `[…var(--x)…]`;
   flag `declared ∩ only-arbitrary`.
3. Add the rule-fires test (seeded violation → non-zero).
4. Relocate the 5–6 at-risk vars (to `:root{}` or literal) and verify rendered
   CSS is unchanged (build + Playwright spot-check at 1440).
5. Wire into `npm run lint` + `gates.sh`; document in qa-checkpoints.md.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-25 HH:mm

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
