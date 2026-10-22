# AE-0498 — Rubric must have at least one criterion

Status: In Development
Tier: T2
Priority: Medium
Type: Bug
Area: Backend + Frontend
Owner: Pedro Marins
Branch: fix/ae-0498-rubric-requires-criterion
Created: 2026-10-22
Updated: 2026-10-22

## Goal

A quality rubric cannot be saved without criteria, in the form or through the API.

## Problem

Dashboard QA (DQ-A-01): a rubric with zero criteria can be created. The form schema
(`frontend/src/schemas/rubric.ts`, `criteria: z.array(rubricCriterionSchema)`) has no minimum, and the
API (`api/schemas/persona_rubric.py`, `criteria = Field(default_factory=list)` on create and
`criteria: list[...] | None` on update) accepts an empty list. A rubric without criteria scores nothing.

## Scope

- Form: `criteria` needs at least one item; "Criar rubrica" / "Salvar alterações" is blocked with the
  field message "Adicione ao menos um critério." under the criteria section.
- API: `POST /api/rubrics` without criteria or with `criteria: []` → 422; `PUT /api/rubrics/{id}` with
  `criteria: []` → 422 (omitting `criteria` on update still keeps the stored criteria).

## Non-Goals

- Existing rubrics are not migrated (prod has 0 rubrics).
- The other rubric polish items (AE-0512).

## Acceptance Criteria

- [ ] Given the rubric form with no criteria, When "Criar rubrica" is clicked, Then save is blocked with
      the field message "Adicione ao menos um critério." and nothing is sent.
- [ ] Given the API, When POST has `criteria: []` (or no `criteria`), Then it returns 422 and nothing is
      stored.
- [ ] Given the API, When PUT has `criteria: []`, Then it returns 422 and the stored criteria are kept;
      a PUT without `criteria` still updates the other fields.

## Gherkin Scenarios

See `backend/tests/features/rubric_requires_criterion_ae0498.feature` and
`frontend/tests/features/rubric-requires-criterion-ae0498.feature`.

## Affected Areas

- [x] Backend (`api/schemas/persona_rubric.py`)
- [x] Frontend (`schemas/rubric.ts`, `rubric-form-model.ts`, `rubric-criteria-list.tsx`, i18n)
- [x] API (OpenAPI artifact: `criteria` required with `minItems: 1` on create)
- [x] Tests
- Database: no change.

## Dependencies

- Blocks: AE-0512 (rubric polish).

## Progress Log

### 2026-10-22

Cause confirmed in both schemas; failing tests first.

## Files Touched

(updated as work lands)

## Test Evidence

(see `.agent/reports/AE-0498.dev-summary.md`)

## QA Report

Pending.

## Blockers

None.
