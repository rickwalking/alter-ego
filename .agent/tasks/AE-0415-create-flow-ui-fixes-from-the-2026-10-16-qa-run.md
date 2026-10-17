# AE-0415 — Create-flow UI fixes from the 2026-10-16 QA run

Status: In Development
Tier: T2
Priority: P1
Type: Bug
Area: Frontend
Owner: Claude (owner-requested fix, QA 2026-10-16)
Agent Lane: developer → qa → release
Branch: fix/ae-0415-create-flow-ui
Kanban Card: TBD
Created: 2026-10-17
Updated: 2026-10-17

## Goal

The create flow shows what each gate reviews, keeps the running state across reloads and
revisions, follows the workflow to the next gate, explains create-form errors, is fully
translated in PT and is accessible. The publish page of an unfinished carousel says it is
not ready instead of offering broken links and mutating actions.

## Problem

QA run 2026-10-16 (`~/alter-ego-qa/2026-10-16-ui/REPORT.md`), re-verified on main 6e7c144:

- **B01 (frontend part):** `create-workflow-panel.tsx` took `Math.min` of the raw stored
  `overall` values and compared it with 70, so a 0-10 answer (8.7) or an unscored 0 blocked
  approval, and the hint never named the slide.
- **B13:** `showPhaseReview` was true only for the Content and Review steps, so the live
  Research and Outline gates showed only a feedback box (the review components existed).
- **B15:** the SSE connect-time snapshot reads the raw checkpoint (`awaiting_human`) while the
  DB row (and `GET workflow/state`) says `in_progress`; the snapshot was merged over the
  fresh state, so a reload mid-run lost the banner and re-enabled revise/auto-fix.
- **B26:** on a 202 the resume hook kept the acted-on gate when it was "ready", so a revise
  showed no running state; the page never followed the workflow to the next gate, and
  `workflow/start` navigated to `?step=outline` whatever the phase.
- **B27:** the banner named the phase just approved, "Processando aprovação… até um minuto"
  appeared twice, and the legacy pipeline step list did not match the editorial phases.
- **B28:** a leftover `phase_progress` label kept the "currently processing" panel on an
  approved project.
- **B30:** the brief preview treated the 404 of a fresh project as an error, and the fresh
  workspace requested `workflow/state` (404 in the console).
- **B18:** an empty Brief fell back to the full topic (≤500) while `niche` allows 200 → 422,
  shown as "HTTP error! status: 422".
- **B32:** the create error stayed after edits/mode switches; no live counters.
- **B31:** create-form labels not tied to inputs, POV thumbnails `alt=""`, template cards were
  `div role=button` with no selection state, no visible focus on inputs/selects.
- **B33:** the preview rendered `v{template_version}` → "vv2".
- **B25:** the publish page of a mid-review carousel offered a 404 PDF, broken slide images,
  rebuild/regenerate/edit/auto-fix, and Radar templates for a POV project.
- **B24 (part):** hardcoded English on the create form, steps bar, summaries, sidebar,
  raw phase ids, board snake_case statuses and the top bars; no dashboard language switcher.

## Scope

1. `persona-score.ts` mirrors `domain/persona_score.py` (≤10 → ×10, 0/missing/non-numeric
   unscored and ignored); the persona hint names each slide under 70 with its score.
2. The Research and Outline gates render `ResearchPhaseReview` / `OutlinePhaseReview`
   (findings with sources; outline titles and key points; hook picker when present).
3. SSE: a same-phase `in_progress → awaiting_human` flip is confirmed with
   `GET workflow/state` before it is applied. While a run executes the panel hides auto-fix
   and locks manual fixes / design recovery.
4. Resume: a 202 adopts the accepted `in_progress` status unless a newer gate (another phase)
   already arrived; the hook exposes `runningAction`; the page follows the workflow to a new
   gate when the owner was on the previous live step (or ahead), never from a historical step;
   `start` navigates to the step of the returned phase.
5. Banner names the running phase (approve → next phase, revise → same phase, unknown →
   neutral); one "Processando…" line; the progress card shows only the live progress detail
   while a run is active (no legacy step list, nothing on approved projects).
6. Brief preview 404 → empty state; the workspace skips the state fetch when the project's
   `current_phase` is `brief`/empty (`useEditorialWorkflow(…, { initialFetch })`).
7. Create form: niche fallback cut at a word boundary to 200; 422 validation errors mapped to
   one localized line per field (`ApiError.detail`); errors clear on any change; live counters.
8. A11y: `htmlFor`/`id` on fields and selects, counters via `aria-describedby`, radio-group
   template cards with `aria-checked`, thumbnail alt text, visible `focus-visible` outline.
9. "vv2" → "v2".
10. Publish page: "not ready yet" notice and no PDF/viewer/rebuild/regenerate/text edit/auto-fix
    until final review or approval; Radar layouts only for Radar IA projects.
11. i18n en/pt for the create form, steps bar, summaries, sidebar, phase names, board
    statuses, top bars, errors, publish page; LanguageSwitcher in the dashboard sidebar.

## Non-Goals

- Backend persona logic (AE-0407 did it); the budget text in `presentation-review-utils.ts`
  and `workspace/phase-review/**` (AE-0414).
- The board's grouping of rejected cards under "Brief" (backend), blog list / violation
  message translations (other tickets).
- Slide viewer counts on a ready project (the viewer is hidden until ready; the count comes from
  the published slide URLs).

## Acceptance Criteria

- [x] AC1: persona scores 84 and 8.7 do not block; 80 and 0 do not block; 6.5 blocks and the
  hint reads "… below 70/100 on Slide 2 (65/100) …".
- [x] AC2: the live Research gate lists findings with sources; the live Outline gate lists
  titles and key points (hook picker when candidates exist).
- [x] AC3: a stale SSE snapshot over an in-progress state is confirmed via GET and does not
  flip the state; a flip to another phase is applied at once.
- [x] AC4: a 202 at the acted-on gate flips to in_progress and waits for the next gate; a newer
  gate that arrived first is kept.
- [x] AC5: while running: banner, no feedback box, no auto-fix, approve disabled.
- [x] AC6: banner after approving research names the outline; after a revise names research.
- [x] AC7: the page follows research → outline from the live step and stays on a historical step.
- [x] AC8: no progress card on an approved project; no legacy step list.
- [x] AC9: preview 404 shows "No draft content yet."; fresh projects skip the state fetch.
- [x] AC10: a 450-char topic with empty brief builds a schema-valid request; the 422 shows
  "Brief / Niche: at most 200 characters" once; errors clear on change; counters show.
- [x] AC11: labels associated; template radios expose `aria-checked`; thumbnail alt set.
- [x] AC12: "v2" renders as "v2".
- [x] AC13: publish page not-ready state before final review; no Radar templates for POV.
- [x] AC14: the PT dashboard shows the create flow, board and sidebar in Portuguese; the
  sidebar has the EN | PT switcher.

## Gherkin Scenarios

- `frontend/tests/features/create-flow-ui-ae0415.feature`

## Delta

### ADDED

- `frontend/src/app/dashboard/create/workspace/persona-score.ts` (+ test)
- `frontend/src/app/dashboard/create/workspace/editorial-phase-labels.ts`
- `frontend/src/app/dashboard/create/use-follow-workflow-step.ts` (+ test)
- `frontend/src/app/dashboard/create/create-error-message.ts` (+ test)
- `frontend/src/app/dashboard/create/[id]/publish/publish-readiness.ts` (+ test)
- `frontend/src/app/dashboard/workflow/localize-board.ts` (+ test)
- Tests: `create-carousel-preview.test.tsx`, `create-draft-blog-preview.test.tsx`,
  `create-workflow-progress.test.tsx`
- `frontend/tests/features/create-flow-ui-ae0415.feature`

### MODIFIED

- Create flow: `create-workflow-panel.tsx`, `create-phase-review.tsx`,
  `create-workflow-controls.tsx`, `create-run-progress-banner.tsx`,
  `create-workflow-progress.tsx`, `create-draft-blog-preview.tsx`,
  `create-carousel-preview.tsx`, `labeled-field.tsx`, `labeled-select.tsx`,
  `section-styles.ts`, `create-topic-section.tsx`, `create-template-section.tsx`,
  `create-theme-section.tsx`, `create-photo-section.tsx`, `project-summary-card.tsx`,
  `brief-step-content.tsx`, `workflow-step-content.tsx`, `create-sidebar.tsx`,
  `create-workspace-sidebar.tsx`, `create-progress-steps.tsx`, `constants.ts`, `helpers.ts`,
  `page.tsx`, `[id]/page.tsx`, `[id]/publish/page.tsx`
- Hooks: `use-editorial-workflow.ts`, `use-editorial-workflow-resume.ts`,
  `use-editorial-workflow-sse.ts`, `hooks/types.ts`
- Shared (minimal, outside the listed scope): `modules/editorial/workspace/types.ts`
  (`personaShortfallDetail` prop), `lib/api-client.ts` (`ApiError.detail`),
  `components/organisms/neon-sidebar.tsx` (language switcher)
- Board: `app/dashboard/workflow/page.tsx`
- i18n: `en.json`, `pt.json`
- Tests updated for the new behaviour: resume/SSE (mutation) tests that asserted the stale-gate
  behaviour, sidebar badge label, template radios.

### REMOVED

- None (the legacy `CarouselProgress` stays for its other users).

## Affected Areas

- Backend: none
- Frontend: create flow, workflow hooks, publish page, board, sidebar
- Database: none
- API: none (reads the existing 422 `detail`)
- Tests: unit + feature
- Docs: none
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0407 (persona score helper), AE-0414 (phase-review files), AE-0315 (run banner)

## Implementation Plan

1. Ticket + feature.
2. Persona util and panel gates (B01, B13).
3. Running state: SSE confirmation, 202 handling, banner, progress, follow (B15, B26-B28).
4. Fresh project (B30), create form (B18, B32, B31), preview (B33).
5. Publish page (B25), i18n + switcher (B24).
6. Gates, PR, CI.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-17

Ticket created from the QA report; all listed bugs implemented with tests; gates run.

## Files Touched

See Delta.

## Test Evidence

See `.agent/reports/AE-0415.dev-summary.md`.

## QA Report

Pending (CI decides).

## Decision Log

- 2026-10-17: B15 is fixed on the client: the SSE snapshot comes from the raw checkpoint, and
  passing the DB status down the stream chain would change four signatures under the 3-arg
  rule. A same-phase running → ready flip is confirmed by `GET workflow/state` (the DB-merged
  source of truth); a real approval lands on another phase and is applied at once, a real
  revise completion costs one GET.
- 2026-10-17: B27 uses the action the owner clicked (`runningAction`); after a reload the
  action is unknown and the banner says "running from the {phase} step" instead of guessing.
- 2026-10-17: B30 skips the mount fetch only when the project row says the workflow never
  started (`current_phase` brief/empty); everything else still fetches.

## Blockers

None.

## Final Summary

Pending.
