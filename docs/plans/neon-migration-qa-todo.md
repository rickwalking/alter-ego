# Neon Shell Migration — QA Remediation Todo

**Branch:** `design-implementation`
**Last updated:** 2026-05-29
**Goal:** Next `/qa-agent` run should PASS all dimensions.

---

## Completed in this pass

- [x] Atomic folder structure: `src/components/atoms/`, `molecules/`, `organisms/`
- [x] Removed `src/components/ui/index.ts` and shadcn compatibility aliases
- [x] Zero `@/components/ui` imports in `src/`
- [x] Phases 3–5: knowledge, blog, chat, workflow, create features → direct Neon imports
- [x] Phase 6: deleted duplicate `workflow-board.tsx`; wired `NeonKanbanBoard`
- [x] Storybook 9 installed + 32 CSF story files
- [x] Adapter tests: workflow, calendar, rubric (+ existing document, blog, persona)
- [x] Strengthened `neon-button` variant tests; updated Stryker paths

---

## Remaining (for full QA PASS)

### Code quality

- [x] Split `src/app/dashboard/chat/page.tsx` (50 lines + subcomponents)
- [ ] Split `src/app/dashboard/rubrics/page.tsx` (388 lines) — proactive
- [x] Replace inline `rgba(0,212,255,...)` in dashboard pages with `@/constants/neon` tokens
- [ ] Update `frontend/CLAUDE.md` structure docs to reflect atoms/molecules/organisms

### Mutation testing (ADR-005 UI break ≥30%, low ≥50%)

- [x] `neon-button.tsx` mutation score **89.29%** (Stryker; tests must not be in `ignorePatterns`)
- [x] Stryker thresholds aligned to ADR-005 UI (break 30%, low 50%, high 65%)
- [ ] Add assertion-based tests for `neon-badge`, `neon-card` variants (not just presence)

### Acceptance criteria (plan)

- [x] Storybook installed with CSF stories (33 files)
- [x] Gherkin for `neon-badge`, `neon-input`, `neon-kanban-board`
- [x] Unit tests for `NeonSidebar`, `NeonTopBar`, `NeonStatsGrid`, `NeonKanbanBoard`
- [ ] Visual regression: Chromatic wired to Storybook (optional Phase 0.5)
- [ ] E2E smoke: dashboard workflow + knowledge upload paths

### Coverage (project target 90%)

- [ ] Repo-wide coverage still ~32% — out of neon scope but blocks global QA PASS

### Security

- [ ] Track Next.js PostCSS advisory ([GHSA-qx2v-qp2m-jg93](https://github.com/advisories/GHSA-qx2v-qp2m-jg93)) — no safe `npm audit fix` yet

### Orphan code

- [x] `WORKFLOW_RESPONSIVE_CSS` removed
- [ ] Audit `features/workflow/components/workflow-kanban-board.tsx` vs dashboard kanban (API vs mock — intentional)

---

## Verification checklist (run before QA)

```bash
cd frontend
npm run typecheck
npm run lint
npm run test -- --run
npm run build
npm run build-storybook   # after stories enriched
rg '@/components/ui' src/ # expect 0 matches
```

---

## Import conventions (post-migration)

| Layer | Path | Example |
|-------|------|---------|
| Atoms | `@/components/atoms/neon-button` | `NeonButton` |
| Molecules | `@/components/molecules/neon-card` | `NeonCard`, `NeonCardHeader` |
| Organisms | `@/components/organisms/neon-sidebar` | `NeonSidebar` |
| Barrel (optional) | `@/components/atoms` | re-export from `index.ts` |

**Never** import `Button`, `Card`, `Badge` shadcn aliases — use `Neon*` only.
