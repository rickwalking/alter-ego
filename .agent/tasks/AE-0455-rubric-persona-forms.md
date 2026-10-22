# AE-0455 — Real create/edit forms for Rubrics and Personas

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: Frontend
Owner: Worker (Claude)
Agent Lane: developer → qa → release
Branch: feat/ae-0455-rubric-form (rubrics), feat/ae-0455-persona-form (personas)
Kanban Card: TBD
Created: 2026-10-21
Updated: 2026-10-21

## Goal

Rubrics and personas are created and edited in real forms instead of a `window.prompt`. One PR per page:
rubrics first, then personas (owner decision, 2026-10-21).

## Problem

AE-0453 site QA, SITE-06 / SITE-09 (prod, 2026-10-21): `/dashboard/rubrics` showed a blank content area with no
rubrics; "New Rubric" opened `window.prompt("Rubric name")` and POSTed `criteria: []` with a fixed
`applicable_content_types: ["carousel"]`; no edit existed; the page strings were English-only.
`/dashboard/personas` "Create Persona" is the same `window.prompt` pattern.

## Scope (rubrics PR)

- Empty state with a create button when the API returns no rubrics.
- Create and edit form: name, description, applicable content types (carousel, blog post, plus any stored
  extra), criteria list with add / remove / move up / move down, and each criterion's fields as
  `RubricCriterion` defines them (name, description, weight, evaluation method, minimum threshold,
  scoring scale, evaluation prompt).
- Client validation mirrors `QualityRubricCreate` / `RubricCriterion` (`src/schemas/rubric.ts`): name 1–255,
  weight and threshold 0–1, method and scale from the backend enums; at least one content type and a
  criterion name are required.
- Server errors shown inline: the API's string `detail` when it sends one, a translated fallback otherwise
  (`ResourceRequestError` in `use-resource-collection`).
- Cancel without saving; unsaved-changes guard (Cancel, in-app links, tab close).
- Edit (PUT) and delete with a confirmation dialog that shows a refusal (the default rubric).
- Keyboard accessible (labels, fieldsets, aria-invalid / aria-describedby, focus on the first invalid field,
  focus on a newly added criterion and the dialog's Cancel); pt/en strings.

## Non-Goals

- No backend change: `POST/PUT/DELETE /api/rubrics` already exist.
- The panel's per-criterion columns (Excellent / Good / Poor) and the `mapQualityRubricToPanelData` copy are
  unchanged.

## Acceptance Criteria

- [x] Empty rubric list shows an explanation and a "Create your first rubric" button.
- [x] Create sends name, description, content types and criteria; the list shows the new rubric.
- [x] Edit loads the stored values and saves with PUT.
- [x] Criteria can be added, reordered and removed from the keyboard.
- [x] Invalid fields block the save, are marked invalid and show translated errors.
- [x] A server refusal is shown in the form, values kept.
- [x] Cancel leaves without saving; unsaved changes ask first.
- [x] Delete asks first and shows a refusal.
- [x] All new strings exist in en and pt.

## Gherkin Scenarios

- `frontend/tests/features/rubric-form-ae0455.feature`

## Affected Areas

- Frontend: `src/app/dashboard/rubrics/`, `src/schemas/rubric.ts`, `src/lib/use-resource-collection.ts`,
  `src/i18n/locales/{en,pt}.json`
- Tests: frontend unit

## Dependencies

- Source: AE-0453 site QA report (SITE-06, SITE-09)

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-21

Rubrics PR: form, empty state, edit and delete built on the existing collection hook; failed requests now
carry the API's string detail. Unit tests for the page, the form model and the collection hook.
Mutation: CI only.

## Files Touched

- frontend/src/app/dashboard/rubrics/page.tsx
- frontend/src/app/dashboard/rubrics/rubric-panel.tsx
- frontend/src/app/dashboard/rubrics/rubric-form.tsx
- frontend/src/app/dashboard/rubrics/rubric-form-model.ts
- frontend/src/app/dashboard/rubrics/use-rubric-form.ts
- frontend/src/app/dashboard/rubrics/rubric-criteria-list.tsx
- frontend/src/app/dashboard/rubrics/rubric-criterion-fields.tsx
- frontend/src/app/dashboard/rubrics/rubric-content-types-field.tsx
- frontend/src/components/molecules/neon-labelled-field.tsx
- frontend/src/components/molecules/neon-confirm-dialog.tsx
- frontend/src/app/dashboard/rubrics/rubrics-empty-state.tsx
- frontend/src/schemas/rubric.ts
- frontend/src/lib/use-resource-collection.ts
- frontend/src/i18n/locales/en.json
- frontend/src/i18n/locales/pt.json
- frontend/tests/features/rubric-form-ae0455.feature
