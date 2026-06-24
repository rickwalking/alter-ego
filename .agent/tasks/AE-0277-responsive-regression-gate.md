# AE-0277 — Responsive-regression gate (no reintroduced frozen layouts)

Status: QA Running
Tier: T1
Priority: Medium
Type: Chore
Area: frontend
Owner: Pedro Marins
Agent Lane: developer → qa
Branch: feat/ae-0277-responsive-regression-gate
Kanban Card: TBD
Created: 2026-06-24
Updated: 2026-06-24
Parent: AE-0272
Depends-On: AE-0273, AE-0274, AE-0275, AE-0276

## Goal

Prevent regression of the responsive work: a CI checker that fails when an audited
dashboard surface reintroduces a layout-freezing inline style. Replaces the v1 plan's
"lightweight grep" with a real gate + rule-fires test (per AE-0180).

## Problem

The epic removes layout-critical inline `style={{}}` (fixed `gridTemplateColumns`, px
`marginLeft`, fixed px `width` on layout containers, `display:"grid"/"flex"` without a
class). Nothing stops a future edit from re-adding them, silently re-breaking mobile.

## Classification (AE-0153 unit-test path)

- **No public/user-visible behavior change** — this is CI/tooling only.
- **Seeded-violation test** included (rule-fires, AE-0180).
- **Affected gate:** new `lint:responsive-dashboard` wired into `npm run lint` +
  `scripts/ci/gates.sh frontend`.
- Reviewer/QA sign-off on the no-`.feature` classification required.

## Scope

- `frontend/scripts/check-responsive-dashboard.mjs` — scans the audited dashboard files
  (an explicit allow-listed file set) for the banned layout-freezing inline patterns;
  non-zero exit on violation, with file:line + the offending snippet.
- `frontend/scripts/check-responsive-dashboard.test.ts` — rule-fires test: a seeded
  fixture with `gridTemplateColumns:"1fr 360px"` makes the checker exit non-zero; the
  real tree passes.
- Wire into `package.json` `lint` chain + gates.

## Non-Goals

- A general repo-wide ESLint rule (neon system uses inline color styles legitimately;
  scoped checker avoids a giant baseline). Backend.

## Rule definitions (tightened per GLM 5.2 review — avoid false positives / dead branches)

- **"layout container"** = a JSX element whose own inline `style` ALSO sets
  `display:"grid"`/`"flex"` OR `gridTemplateColumns` (i.e. the element that owns the
  layout), not a decorative leaf.
- **`gridTemplateColumns` branch:** any inline `gridTemplateColumns` with a fixed track
  (px or bare `1fr`/`repeat(N,...)`) → flag.
- **`marginLeft` branch:** ONLY flag px `marginLeft`/`margin-left` **≥ 64px** OR on a
  layout container (shell/content offset). Small spacing (`6px`, `8px`, e.g.
  `create-workspace-sidebar.tsx:114`, `calendar-toolbar.tsx:56`) is NOT flagged.
- **fixed `width` branch:** flag fixed px `width` ONLY on a layout container (per above).
- **`display:grid/flex` branch:** flag inline `display:"grid"`/`"flex"` only when the
  SAME element has no responsive Tailwind layout class (`grid`/`flex`/`md:`/`lg:` prefix)
  in its `className` — "same element", not "nearby".

## Acceptance Criteria

> **Branch-count reconciliation (post external-QA):** the v1 "four branches" is delivered
> as **three precisely-definable branches** (gridTemplateColumns / marginLeft≥64 /
> fixed-width≥200 on a flex-grid container). The 4th "bare `display:flex` without a
> responsive class" branch is **intentionally dropped** — the epic deliberately keeps
> non-layout-critical inline `display:flex` rows, so flagging all of them would
> false-positive on the intended end state and fail the "exits 0 on current tree" AC.
> Rationale documented in the script header. (GLM I5 said "define precisely or drop".)

- [ ] `check-responsive-dashboard.mjs` implements the three branches above with the stated
      qualifiers (no false-positive on `6px`/`8px` spacing marginLeft).
- [ ] **Allow-list = the union of every file modified by AE-0273/0274/0275/0276** (shell +
      create flow incl. workspace section grids + publish `regenerate-strategy-section` +
      listings incl. rubric-panel + data-dense incl. calendar-header/toolbar). A sync
      check fails if a known-responsive file is absent.
- [ ] Exits 0 on the current (post-0273..0276) tree; exits non-zero on a seeded violation.
- [ ] **Per-branch rule-fires tests** (AE-0180): each of the three detection branches has a
      seeded fixture that makes the checker exit non-zero — not just `gridTemplateColumns`.
- [ ] Added to `npm run lint` and `scripts/ci/gates.sh frontend`; documented in
      `docs/guides/qa-checkpoints.md`. Passes in CI without external keys.
- [ ] `gates.sh frontend` green.

## Gherkin Scenarios

```gherkin
Feature: Responsive-dashboard regression gate

  Scenario: Gate passes on the responsive tree
    When check-responsive-dashboard runs on the current dashboard files
    Then it exits zero

  Scenario: Gate fires on a reintroduced frozen layout
    Given a dashboard file with inline gridTemplateColumns "1fr 360px"
    When check-responsive-dashboard runs
    Then it exits non-zero and reports the file and line
```

## Delta

### ADDED
- `scripts/check-responsive-dashboard.mjs` + `.test.ts`; `lint:responsive-dashboard`
  npm script; gate wiring; qa-checkpoints doc entry.

## QA Checklist

- [ ] Rule-fires test green; gate in lint chain; no external keys needed.
- [ ] Allow-list of audited files documented in the script header.
</content>


## Progress Log

- 2026-06-24 — Implemented per ticket scope; layout-critical inline styles migrated to
  Tailwind responsive utilities. Full `gates.sh frontend` reproduced green (17/17).

## Test Evidence

```
GATES_JSON: {"pass":17,"fail":0,"skip":0} — full frontend suite green (lint incl.
responsive-dashboard gate, boundaries, dup, component-types, i18n, typecheck, build,
test 936+, mutation, dead-files, integrity, format, schema-drift).
```

- Typecheck + targeted vitest suites pass; no new jscpd duplication; integrity 0 net-new.
