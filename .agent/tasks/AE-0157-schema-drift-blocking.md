# AE-0157 — Reconcile OpenAPI/Zod schema drifts to 0 + flip the drift check to blocking

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Frontend/CI
Owner: developer
Agent Lane: planner → architect → developer → qa → release
Branch: feat/phase-8-legacy-removal
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Reconcile the 24 advisory OpenAPI/Zod schema-drift findings (AE-0141) to 0, then flip the schema-drift check from advisory to blocking in CI.

## Problem

AE-0141 shipped the drift check as advisory with 24 pre-existing frontend Zod vs backend OpenAPI divergences (nullability, missing/extra fields). The exit gate wants it blocking once clean.

## Scope

Reconcile each of the 24 drifts behavior-preservingly (align the frontend Zod schema to the actual API contract, or document an intentional divergence as an exclusion); regenerate the OpenAPI artifact; flip check:schema-drift to --strict / blocking in gates.sh + CI. Validate that genuine fixes don't change runtime parsing behavior.

## Non-Goals

- No backend API change (align the frontend to the API, not vice-versa, unless a real backend bug is found -> separate ticket).
- No silencing drifts by widening ignores without justification.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [x] The 24 drift findings SHALL reach 0 (fixed or justified-excluded)
- [x] The schema-drift check SHALL be flipped to blocking (--strict) in gates.sh + CI and pass
- [x] typecheck + lint + 822 tests + build green; no runtime parsing behavior change

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (back-end gates.sh + check-integrity + arch-ratchet; front-end typecheck/lint/boundaries/url/circular/tests/build).

## Dependencies

- Blocks: —
- Blocked by: AE-0153
- Related: AE-0152

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 8 breakdown).

## Files Touched

- `frontend/src/schemas/chat.ts` — `messageSchema.sources` + `chatResponseSchema.sources`: `z.unknown()` → `z.unknown().optional()` (API `sources` is optional; kept permissive `unknown` so parsing behavior is unchanged).
- `frontend/src/schemas/knowledge.ts` — added `scope: z.string()` + `is_public: z.boolean()` to `documentSchema` and `documentUploadResponseSchema` (API-required, non-null); added `scope`/`is_public` as `.optional()` to `createDocumentRequestSchema` (API-optional).
- `frontend/src/schemas/carousel.ts` — `carouselProjectResponseSchema`: added `primary_color`/`accent_color`/`background_color` (`z.string().nullable()`, API-required-nullable), `image_model`/`image_style` (`z.string().optional()`), `is_public` (`z.boolean().optional()`), `current_phase`/`phase_status`/`error_message`/`output_dir` (`z.string().nullable().optional()`), `research_sources`/`slides` (`z.array(z.unknown()).optional()`); `carouselSlideResponseSchema`: removed `project_id` + `image_prompt` (EXTRA-FRONTEND — the `GET /{id}/slides` endpoint returns `list[CarouselSlideResponse]` which has neither), added `image_path` (`z.string().nullable().optional()`) + `updated_at` (`z.string()`).
- `frontend/package.json` — `check:schema-drift` now runs `--strict` (blocking).
- `scripts/ci/gates.sh` — updated the schema-drift gate comment (advisory → blocking, AE-0157).
- `.github/workflows/frontend-quality-gates.yml` — `schema-drift-advisory` job → `schema-drift` (removed `continue-on-error: true`; now blocking).
- Test fixtures updated to the aligned contract: `frontend/src/schemas/carousel.test.ts`, `frontend/src/lib/server-fetch.test.ts`, `frontend/src/modules/knowledge/adapters/document-adapter.test.ts`, `frontend/src/modules/knowledge/components/document-card.test.tsx`, `frontend/src/modules/knowledge/components/document-list.test.tsx`, `frontend/src/modules/publishing/blog/adapters/blog-post-adapter.test.ts`, `frontend/src/modules/publishing/distribution/components/regenerate-strategy-section.test.tsx`.

## Test Evidence

- `node scripts/check-schema-drift.mjs` → "No drift across mapped schemas"; `--strict` gate (`gates.sh frontend:schema-drift`) PASS.
- `npm run typecheck` — clean.
- `npm run lint` — PASS (eslint --quiet + boundaries 0 + url 26 + circular 0 + component-types 57/57).
- `gates.sh frontend:test` — PASS (823 tests).
- `npm run build` — production build succeeded.
- `gates.sh frontend:integrity` — PASS, 0 warnings (flipping a gate stricter is not gaming).

## QA Report

Pending (Phase 8 end-of-phase QA on the full branch).

## Decision Log

- **EXTRA-FRONTEND-FIELD (`carouselSlideResponseSchema.project_id`/`image_prompt`)**: investigated the backend — `GET /carousels/{id}/slides` returns `list[CarouselSlideResponse]` (`api/schemas/carousel.py`), which has NO `project_id`/`image_prompt`. The frontend was over-modeling (and `project_id` was even *required*, which would have rejected real responses). No frontend consumer reads those off the slides-query result (the `project_id`/`image_prompt` hits elsewhere are the separate editorial `SlideImagePrompt`/`EditorialWorkflowState` types). Removed them — contract-aligning, not a backend change.
- **`sources` kept as `z.unknown().optional()`** rather than a typed array: the static drift checker treats bare `z.unknown()` as required-present (hence the NULLABILITY-MISMATCH); adding `.optional()` resolves it while keeping the permissive `unknown` parse so no runtime behavior changes.
- **Added API-optional fields as `.optional()`/`.nullable().optional()`** and API-required-nullable as `.nullable()`, matching the OpenAPI nullability exactly so no new mismatch is introduced; previously these fields were silently stripped by Zod, so no existing consumer is affected.

## Blockers

None.

## Final Summary

OpenAPI↔Zod drift reconciled from 24 findings to 0 by aligning the frontend Zod schemas to the generated OpenAPI contract (chat/knowledge/carousel), then flipped the schema-drift check to blocking (`--strict`) across the npm script, `gates.sh`, and the CI job (advisory → required). No backend API change; no runtime parsing behavior change (added fields were previously stripped; one over-modeled required slide field that would have rejected real responses was removed). Full frontend gate suite green.
