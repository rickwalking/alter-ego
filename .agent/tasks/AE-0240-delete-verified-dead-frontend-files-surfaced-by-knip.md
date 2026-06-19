# AE-0240 — Delete verified-dead frontend files surfaced by knip

Status: Intake
Tier: T2
Priority: Medium
Type: Quality
Area: frontend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Remove genuinely-dead frontend files (no static or dynamic references) to cut dead
weight, after a per-file proof that each is unreferenced. **Barrels and the personas
route are explicitly out of scope** (see AE-0241 and Non-Goals).

## Problem

`knip` reports 21 "unused" frontend files. A kaizen triage (Explore, import-grep)
classified ~9 as genuinely dead (no importers anywhere): stray provider, unused
constants, unused schema files, an unused test fixture, and two empty post-migration
type barrels. The remaining files are design-system barrels (AE-0241), bounded-context
module barrels (intentional, keep), or personas-route files that are still wired to a
live route — none safe to delete here. The dead-file gate (AE-0178/knip) is advisory,
so this debt does not self-clear.

Reports: `.agent/reports/kaizen-session-2026-06-18c.{signal,plan,skeptical-review}.md`.

## Scope — candidate dead files (each requires per-file proof before deletion)

- `src/components/providers/locale-provider.tsx`
- `src/constants/documents.ts`
- `src/constants/rubrics.ts`
- `src/schemas/neon-button.ts`
- `src/schemas/neon-progress-bar.ts`
- `src/schemas/neon-tab.ts`
- `src/test/fixtures/data.ts`
- `src/modules/conversation/types/index.ts` (empty post-migration barrel)
- `src/modules/knowledge/types/index.ts` (empty post-migration barrel)

## Non-Goals

- **Do NOT** delete the design-system barrels (`components/atoms|molecules/index.ts`) or
  any bounded-context module barrel — those are an architectural decision (AE-0241).
- **Do NOT** delete `src/app/dashboard/personas/*` — the personas route is still live
  (it appears in the raw-`fetch` inventory); its removal belongs to the legacy-UI work,
  not here.

## Acceptance Criteria

- [x] For **each** file deleted, evidence is recorded that it is unreferenced (see
      Test Evidence): repo-wide import-path search returned only historical doc
      mentions (no code import), no sibling/parent barrel re-exports them, and each
      exported symbol appears only in its own file (the lone `createDocument`
      collision is a separate local hook/mock, not the fixture).
- [x] Any candidate that turns out to be referenced is **kept** — none were; all 9
      proved dead.
- [x] After deletion: `npm run typecheck`, `npm run build`, `npm run test` green;
      `bash scripts/ci/gates.sh frontend` reproduced at the wave level (see dev-summary).
- [x] `knip` reports correspondingly fewer unused files: 21 → 12; the deleted set no
      longer appears (remaining 12 are the barrels of AE-0241 + the live personas
      route, both out of scope here).

## Gherkin Scenarios

```gherkin
Feature: Delete only provably-dead frontend files

  Scenario: A candidate is unreferenced
    Given a repo-wide search for the file and its exports finds no importer
    When the file is deleted
    Then typecheck, build, and tests stay green

  Scenario: A candidate turns out to be referenced
    Given a repo-wide search finds a dynamic import of the file
    Then the file is kept and the reference is documented
```

## Delta

### REMOVED
- The verified-dead files listed in Scope.

### MODIFIED
- None (deletions only; if a barrel re-exports a deleted file, update it — but barrels
  here are empty/post-migration).

### ADDED
- None.

## Affected Areas

- Frontend: dead-file removal.
- Tests: build/typecheck/test must stay green; the deleted test fixture must be unused.
- Deployment: none (dead code).
- Docs: none.

## Dependencies

- Blocks: shrinks the knip baseline; complements AE-0241.
- Blocked by: none.
- Related: AE-0178 (knip advisory gate), AE-0241 (barrel policy), `docs/plans/frontend-legacy-removal.md`.

## Implementation Plan

1. For each candidate, run the repo-wide reference proof; bucket into delete / keep.
2. Delete the proven-dead set in one commit.
3. Run typecheck + build + test + `gates.sh frontend`; record evidence.
4. Re-run knip to confirm the baseline shrank.

## Test Classification (CLAUDE.md AE-0153)

- **Pure refactor — no public/user-visible behavior change** (removing unreferenced
  code). **Unit/existing tests + green build suffice; no `.feature` required.**
- **Proof obligation:** per-file repo-wide reference search (the "seeded" evidence that
  each file is truly unused) + green typecheck/build/test as the safety net.
- **Affected gates:** `frontend` typecheck/build/test, knip dead-file advisory.
- Reviewer/QA to sign off on the no-`.feature` classification.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (dynamic imports, file-route conventions)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:00

Created by kaizen session-2026-06-18c (user asked to triage the knip report). Cold-
critic (opencode) required per-file repo-wide proof (knip is heuristic) and that the
barrel-policy decision be split out (→ AE-0241).

## Files Touched

### REMOVED (all 9 proved dead)
- `src/components/providers/locale-provider.tsx`
- `src/constants/documents.ts`
- `src/constants/rubrics.ts`
- `src/schemas/neon-button.ts`
- `src/schemas/neon-progress-bar.ts`
- `src/schemas/neon-tab.ts`
- `src/test/fixtures/data.ts`
- `src/modules/conversation/types/index.ts`
- `src/modules/knowledge/types/index.ts`

## Test Evidence

Per-file reference proof (repo-wide):
- Import-path search (`rg --no-ignore-vcs` over `src` + `docs` for each module
  path) found **no code imports** — only historical markdown mentions of
  `schemas/neon-button` (neon-shell-migration-complete.md) and `knowledge/types`
  (REMEDIATION_PLAN.md).
- No sibling/parent barrel (`src/schemas`, `src/constants`, `components/providers`,
  `src/test/fixtures`) re-exports any candidate; the two `types/index.ts` are
  comment-only post-migration barrels with no importer.
- Exported-symbol search: every symbol (`LocaleProvider`, `neon*Schema`,
  `NEON_BUTTON_DEFAULTS`, `CONTENT_TYPE_BLOG_POST`, `SUPPORTED_EXTENSIONS`,
  `mock*`, …) appears only in its own file. The single `createDocument` hit
  elsewhere is `useCreateDocument()` + a `vi.fn()` mock in knowledge-base-interface
  — a different symbol; that file does not import the fixture.

Post-deletion verification:
```
$ npm run typecheck          # tsc --noEmit, clean
$ npm run test -- --run      # 93 files, 896 tests passed
$ npm run build              # next build OK (full route tree emitted)
$ npx knip --include files   # 21 → 12 unused files; deleted set gone
```
(`knip`/`jscpd` were absent locally — installed via `npm ci`; this is the exact
AE-0239 scenario.)

## QA Report

Pending.

## Decision Log

- **Critic [INFO] knip is a heuristic** — ACCEPTED: each deletion requires a repo-wide
  `rg --no-ignore-vcs` proof (dynamic imports/config included) + green build/test, not
  knip's word alone.
- **Critic [INFO] separate dead-file deletion from barrel policy** — ACCEPTED: this
  ticket deletes only uncontroversial dead files; the barrel convention is AE-0241.
- **Personas files excluded** — the route is still live (appears in the raw-`fetch`
  inventory); deletion belongs to legacy-UI removal, not here.

## Blockers

None.

## Final Summary

Pending.
