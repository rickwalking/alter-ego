# AE-0132 — Publishing import contracts + exit gate + baseline ratchet + deferred-cutover docs

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0132-publishing-import-contracts
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Add Import Linter contracts enforcing the publishing exit gate (application/domain isolation; public-facade; publishing imports no editorial/presentation internals), ratchet the AE-0082 baseline down, and document publishing as a worked example INCLUDING the deferred auto-publish cutover + embedded-column drop. Mirrors AE-0103/0112/0122.

## Problem

The publishing boundary + the acyclic direction must be CI-enforced, and the deferred behavior-change/destructive-drop must be explicitly recorded so a later phase executes them with consent.

## Scope

- Add contracts via render_importlinter: publishing-application-isolation (application/domain forbidden from frameworks/get_container/infrastructure — carousel/blog ORM only via the publishing ACL) + publishing-public-facade + publishing-no-editorial-presentation (publishing imports no editorial/presentation internals). Name the publishing ACL as the only allowed carousel/blog-ORM path.
- Regenerate .importlinter; ratchet the AE-0082 baseline DOWN (api->infra / get_container) or hold; --check PASS; demonstrate+revert violations.
- Update module-conventions.md §13 with publishing as a worked example + the additive-migration/outbox patterns + the checkpoint-drain re-affirmation.
- Document the DEFERRED follow-up: the auto-publish behavior cutover (approval≠release becomes two user actions) + the destructive embedded-column drop (drain-gated, post-migration-window), with the AE-0111 contract split already in place.

## Non-Goals

- No weakening of existing contracts.
- No behavior change (CI/docs only).
- No execution of the deferred cutover/drop.

## Modularization Alignment (2026-06-15)

Phase 6 of the modularization plan (§Phase 6). **Behavior-preserving + additive-only** for the IN scope — blog/publish/distribution/calendar/board/analytics responses + the public carousel /blog stay byte-identical; the migration is ADDITIVE (add origin + backfill; NO column drop); the outbox is ADDITIVE (alongside the existing after-commit publish); NO renames. The auto-publish behavior cutover + the destructive embedded-column drop are DEFERRED (documented follow-up; the approval≠release contract is already split in AE-0111). Follow `docs/architecture/module-conventions.md` + the modules/editorial+presentation pattern; reuse the platform UoW, the QA-guardian gates, and the AE-0103/0112/0122 import-contract + ratchet pattern; compose via DI at the edge (no get_container in module code). publishing is invoked BY editorial/presentation via the facade (acyclic; publishing imports no editorial/presentation internals). Precondition: Phase 5 (PR #19) merged. The checkpoint-drain rule applies to any schema-modifying migration (Phase 6's is additive ⇒ no drain needed).

## Acceptance Criteria

- [ ] Import Linter contracts SHALL isolate publishing.application/domain (no frameworks/get_container/infrastructure; carousel/blog ORM only via the publishing ACL), enforce the public facade, and forbid publishing importing editorial/presentation internals; lint-imports KEEPS them
- [ ] WHEN new code violates any boundary THE contract SHALL fail (demonstrated, reverted)
- [ ] THE AE-0082 baseline/--check SHALL ratchet DOWN or hold and stay PASS
- [ ] module-conventions.md SHALL document publishing as a worked example incl. the additive-migration + outbox patterns
- [ ] THE deferred auto-publish cutover + embedded-column drop SHALL be explicitly documented as a consent-gated follow-up; gates.sh + check-integrity + full suite green

## Gherkin Scenarios

Not applicable — CI/docs deliverable; falsifiability demonstrated by reverted violations.

## Delta

### ADDED

- publishing contracts in render_importlinter; module-conventions §13

### MODIFIED

- backend/.importlinter (regenerated); scripts/metrics/import_baseline.py (baseline constants)

### REMOVED

- None

## Affected Areas

- Backend: publishing module
- Frontend: none (Phase 7)
- Database: none (additive-only if any)
- API: none yet
- Tests: contract/behavior tests
- Docs: module-conventions §13
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0123 (closes epic)
- Blocked by: AE-0128, AE-0129, AE-0130, AE-0131
- Related: AE-0103, AE-0112, AE-0122, AE-0123

## Implementation Plan

1. Add the publishing contracts to render_importlinter; regenerate .importlinter.
2. Ratchet baseline; demonstrate+revert violations.
3. Document §13 + the deferred cutover/drop.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 6 breakdown).

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
