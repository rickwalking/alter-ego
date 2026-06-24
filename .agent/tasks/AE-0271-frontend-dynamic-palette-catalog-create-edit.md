# AE-0271 — P4: frontend dynamic palette catalog + create/edit (gate retarget)

Status: QA Running
Tier: T2
Priority: Medium
Type: Feature
Area: frontend
Owner: Pedro Marins
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0271-frontend-palette-catalog
Kanban Card: TBD
Created: 2026-06-23
Updated: 2026-06-23

## Goal

Render the palette catalog dynamically from `GET /palettes` (roots ∪ active custom) and
let users create/edit/archive custom palettes from the UI, replacing the hardcoded theme
lists. Co-deploys with AE-0270 (flips its feature flag). Visual/UX design delegated to
the `impeccable` skill.

## Problem

Today the create page renders a hardcoded `CAROUSEL_THEMES`/`THEME_LABEL_KEYS`/
`LIGHT_THEME_KEYS` list guarded by the AE-0266 palette-drift gate. Custom palettes (from
AE-0270) are invisible until the FE consumes the API dynamically — and the drift gate
would stay green-but-wrong during any gap (skeptical G6), so this must co-ship with P3.

## Scope

- Catalog view + create/edit form consuming `GET /palettes`.
- Replace hardcoded theme constants with the dynamic catalog.
- Retarget the palette-drift gate; flip the AE-0270 feature flag.

## Non-Goals

- Backend CRUD (AE-0270). Per-user palettes (global — D2).

## Acceptance Criteria

- [x] Create-page theme dropdown renders roots ∪ active custom from the API (no hardcoded
      `CAROUSEL_THEMES`/`THEME_LABEL_KEYS`/`LIGHT_THEME_KEYS` — removed from create.ts;
      `buildThemeOptions` builds auto + roots + customs from `GET /palettes`).
- [x] Create/edit form (modal): name, three colours (native picker + hex, **live preview
      swatch**), mode; **image style shown as auto-derived (read-only)**; keyword chip
      input surfacing the guard rules.
- [x] Edit + archive (soft-delete, confirm step) for custom palettes; roots read-only
      with a "root" badge.
- [x] **Drift gate retargeted (G6):** `check-palette-drift.mjs` narrows to the still-static
      IMAGE_PRESETS surface (theme list is now dynamic); AE-0180 rule-fires test + Gherkin
      updated to seed IMAGE_PRESETS drift.
- [x] **Co-deploys with AE-0270** — `feature_flag_palette_catalog` default flipped to True.
- [x] i18n: roots keep en/pt labels (from the API `label_en`/`label_pt`); custom palettes
      show their single user-typed name (O3); new `palettes` namespace in en + pt.
- [x] FE visual/UX built via the `impeccable` skill (product register; Neon design system).
- [x] `npm run lint` + `typecheck` + tests green; **`gates.sh frontend` 17/17 PASS**.

## Gherkin Scenarios

```gherkin
Feature: Dynamic palette catalog in the create flow

  Scenario: A newly created custom palette appears in the dropdown
    Given a custom palette "Aurora" was created via the API
    When the user opens the create page
    Then "Aurora" appears in the theme dropdown alongside the root palettes

  Scenario: Image style is shown as derived, not chosen
    Given the user creates a palette with mode "light"
    Then the form shows image style "flat_editorial" as read-only

  Scenario: Drift gate no longer guards a hardcoded list
    Given the FE renders the catalog from the API
    When the palette-drift gate runs
    Then it checks only the still-static surface and passes
    And its rule-fires test still errors on a seeded drift of that surface

  Scenario: Empty custom catalog shows only root palettes
    Given no custom palettes have been created yet
    When the user opens the create page
    Then the dropdown shows the root palettes only
    And the catalog view shows an empty-state prompt to create the first palette
```

## Delta

### ADDED
- Catalog view + create/edit components; API hook; retargeted drift gate.
### MODIFIED
- Create page; `check-palette-drift.mjs` + its rule-fires test; i18n.
### REMOVED
- Hardcoded `CAROUSEL_THEMES`/`THEME_LABEL_KEYS`/`LIGHT_THEME_KEYS` in `create.ts`.

## Affected Areas

- Frontend: create page, catalog/create-edit UI, API hook, i18n
- Tests: catalog render, create/edit happy + validation, gate rule-fires
- Deployment: **co-deploy with AE-0270** (flag on together)

## Dependencies

- Blocks: —
- Blocked by: AE-0269 (resolver/API), AE-0270 (CRUD — co-deploy)
- Related: AE-0267 (epic), AE-0266 (drift gate it retargets)

## Implementation Plan

1. API hook + catalog render. 2. Create/edit form (impeccable design). 3. Retarget drift
gate + rule-fires test. 4. Flip feature flag; co-deploy with AE-0270.

## QA Checklist

- [ ] Security reviewed (XSS on name; no secrets)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (empty catalog, archived hidden, validation errors)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-23
Created from AE-0267 planner breakdown.

### 2026-06-24 — Dev Complete
Built the dynamic dropdown + `/dashboard/palettes` catalog (impeccable), retargeted
the drift gate, flipped the feature flag (co-deploy go-live). 17/17 frontend gates
green; backend flag-flip tests green. Status → Dev Complete.

## Files Touched
- **FE data**: `schemas/palette.ts` (new), `modules/palette/{index,queries,hooks/use-palettes}.ts`
  (new — barrel public contract), `constants/api.ts` (palette endpoints + PATCH),
  `schemas/carousel.ts` (theme max 30→64 for custom UUIDs).
- **Create flow**: `app/dashboard/create/theme-options.ts` (new mapper) + test,
  `create/page.tsx` (fetch catalog), `workspace/create-theme-section.tsx` (render from
  props) + test, `create/helpers.ts`, `constants/create.ts` (removed the 3 hardcoded
  theme consts + isLightTheme).
- **Catalog UI (impeccable)**: `app/dashboard/palettes/` — `page.tsx`, `palette-card`,
  `palette-swatch`, `palette-color-input`, `palette-form-modal`, `palette-keywords-field`,
  `palettes-empty-state`, `use-palette-form`, `derived-image-style` (+ 3 tests).
- **Nav + i18n**: `constants/dashboard-routes.ts`, `components/layout/{header,mobile-nav}.tsx`,
  `i18n/locales/{en,pt}.json` (nav.palettes + `palettes` namespace).
- **Gate retarget**: `scripts/check-palette-drift.mjs` (narrowed to IMAGE_PRESETS),
  `src/scripts/palette-drift.test.ts`, `tests/features/palette-drift-gate.feature`,
  `tests/features/palette-catalog-ui.feature` (new), `scripts/url-inventory.snapshot.json`.
- **Backend**: `infrastructure/config/settings.py` — flag default False→True (co-deploy).

## Test Evidence
```
npx vitest run (palette + theme-options + create-theme-section + palette-drift)  # 27 passed
GATES_BASE_REF=origin/main bash scripts/ci/gates.sh frontend
  → GATES_JSON: {"pass":17,"fail":0,"skip":0} (lint, component-types, format, build,
    typecheck, test, mutation 84.86%, integrity, schema-drift, dead-code/files all PASS)
backend: pytest tests/unit/api/test_feature_flags.py test_palette_routes.py  # 15 passed
GATES_BASE_REF=origin/main bash scripts/ci/check-integrity.sh {backend,frontend}
  → PASS, 0 net-new blockers, 0 warnings (both scopes)
```

## QA Report
Pending (handing off to external QA).
## Decision Log
D1, D3, O3; G6 (gate retarget + co-deploy) — see arch-plan.
## Blockers
None.
## Final Summary
Pending.
