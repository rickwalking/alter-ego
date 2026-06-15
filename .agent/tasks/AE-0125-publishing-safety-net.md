# AE-0125 — Publishing byte-identical safety net (blog/publish/distribution/calendar/board/analytics) + Gherkin

Status: Ready
Tier: T2
Priority: High
Type: Tests
Area: Tests
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: test/ae-0125-publishing-safety-net
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Build the byte-identical safety net for the publishing surface before any refactor: committed response snapshots for blog-post CRUD, the public carousel /blog + /blog/{lang}, publish/instagram, calendar, workflow-board, and analytics; + Gherkin for publish/distribution/calendar (no scenarios exist today). The gate AE-0128/0129/0131 diff against.

## Problem

Phase 6 moves blog/publishing/distribution + read routes behind facades + adds an additive migration; without an enforceable byte-identical baseline the refactor or migration could silently change a response.

## Scope

- Snapshot blog-post CRUD responses, the public carousel /blog + /blog/{lang}, publish-instagram + generate-caption, content-calendar, workflow-board, and editorial-analytics responses — volatile normalized via a diff helper.
- Add Gherkin for publish (approval→release), distribution (caption/linkedin/instagram), and calendar/board scenarios; each backed by an executing test.
- Stub external channels (Meta/Instagram, LLM) deterministically; no live keys; pin env-sensitive settings (DEBUG) for local/CI determinism (AE-0097 lesson).
- Green baseline, NO production code modified.

## Non-Goals

- No production code change.
- No new publish behavior (snapshots capture CURRENT behavior incl. the auto-publish conflation).

## Modularization Alignment (2026-06-15)

Phase 6 of the modularization plan (§Phase 6). **Behavior-preserving + additive-only** for the IN scope — blog/publish/distribution/calendar/board/analytics responses + the public carousel /blog stay byte-identical; the migration is ADDITIVE (add origin + backfill; NO column drop); the outbox is ADDITIVE (alongside the existing after-commit publish); NO renames. The auto-publish behavior cutover + the destructive embedded-column drop are DEFERRED (documented follow-up; the approval≠release contract is already split in AE-0111). Follow `docs/architecture/module-conventions.md` + the modules/editorial+presentation pattern; reuse the platform UoW, the QA-guardian gates, and the AE-0103/0112/0122 import-contract + ratchet pattern; compose via DI at the edge (no get_container in module code). publishing is invoked BY editorial/presentation via the facade (acyclic; publishing imports no editorial/presentation internals). Precondition: Phase 5 (PR #19) merged. The checkpoint-drain rule applies to any schema-modifying migration (Phase 6's is additive ⇒ no drain needed).

## Acceptance Criteria

- [ ] THE committed snapshots SHALL capture blog CRUD + public carousel /blog(+lang) + publish-instagram/caption + calendar + board + analytics responses as byte-identical baselines with a diff helper
- [ ] THE distribution/channel paths SHALL use deterministic stubs (no live Meta/LLM key) and pin env-sensitive settings
- [ ] Publish/distribution/calendar Gherkin SHALL be added; each scenario backed by an executing test (no orphans)
- [ ] THE snapshots SHALL capture CURRENT behavior (incl. the approval→is_public publish flow) so AE-0128 diffs to zero
- [ ] WHEN `uv run pytest` runs THE safety-net suite SHALL pass with NO production code modified (green baseline)

## Gherkin Scenarios

```gherkin
Feature: Publishing safety net (representative)

  Scenario: public carousel blog unchanged
    Given a public carousel
    When GET /api/carousels/{id}/blog runs
    Then the response matches the committed snapshot

  Scenario: blog post CRUD shapes unchanged
    When the /api/blog-posts endpoints run
    Then responses match the committed snapshots
```

## Delta

### ADDED

- tests/integration/test_publishing_safety_net.py
- tests/snapshots/publishing/* + diff helper
- publish/distribution/calendar Gherkin

### MODIFIED

- tests/features/* (audit/extend)

### REMOVED

- None

## Affected Areas

- Backend: none
- Frontend: none (Phase 7)
- Database: none (additive-only if any)
- API: none
- Tests: safety net + snapshots
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0128, AE-0129, AE-0131
- Blocked by: None
- Related: AE-0097, AE-0116, AE-0123

## Implementation Plan

1. Audit blog/publish/calendar/board/analytics tests.
2. Snapshot responses + add Gherkin; stub channels; pin DEBUG.
3. Green baseline; no src/ change.

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
