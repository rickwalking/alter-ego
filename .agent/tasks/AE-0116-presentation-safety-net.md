# AE-0116 — Presentation byte-identical safety net (responses + FileResponse bytes + artifact URLs)

Status: Ready
Tier: T2
Priority: High
Type: Tests
Area: Tests
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: test/ae-0116-presentation-safety-net
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Build the byte-identical safety net for the presentation surface before any refactor: committed snapshots for the media/preview/slides/design/strategies/creator-asset responses (JSON schemas) AND assertions on FileResponse content-type/headers/bytes for the PDF/JPEG endpoints + artifact URL strings, using a DETERMINISTIC image-provider stub. The gate AE-0118/0120/0121 diff against.

## Problem

Phase 5 moves presentation routes/services/persistence behind a facade + ACL; without an enforceable byte-identical baseline (incl. binary artifact bytes/headers and artifact URLs) the refactor could silently change a response schema, a file's bytes/content-type, or an artifact path.

## Scope

- Snapshot the JSON responses for GET design, blog, blog/{lang}, slides, /strategies, and the creator-asset endpoints (CarouselDesignResponse/CarouselBlogResponse/i18n/CarouselSlideResponse/StrategyListResponse/CreatorAssetResponse) — volatile fields normalized via a diff helper.
- Assert the FileResponse endpoints (pdf, images/{fn}, slide-images/{lang}/{fn}, download) return identical content-type/headers and byte content (or a stable digest) + the artifact URL/path strings.
- Use a DETERMINISTIC image-provider stub (fixed bytes) — no live DALL-E/Gemini (no API keys in this env); pin env-sensitive settings (DEBUG) for local/CI determinism (AE-0097 lesson).
- Audit/extend presentation Gherkin (media access, design/slide rendering, strategy apply, creator-asset upload); back each scenario with an executing test. Green baseline, no production code modified.

## Non-Goals

- No production code change.
- No distribution/blog-write snapshots beyond the read endpoints already public (Phase 6 owns distribution).

## Modularization Alignment (2026-06-15)

Phase 5 of the modularization plan (§Phase 5). **Behavior-preserving** — presentation response schemas (design/blog/slide/strategy/creator-asset), artifact URLs, `FileResponse` bytes/headers (PDF/JPEG), and the `artifact_version`↔`lock_version` activation CAS stay byte-identical; NO renames (later phases). Follow `docs/architecture/module-conventions.md` + `modules/_template` + the proven `modules/editorial` pattern; reuse the `platform/database` UoW, the QA-guardian gates, and the AE-0103/AE-0112 import-contract + baseline-ratchet pattern; compose via DI at the edge (no get_container in module code). Presentation does NOT own blog/distribution (caption/linkedin), publishing/is_public, persona, or workflow state (Phase 6 / editorial). Precondition: Phase 4 (PR #18) merged. The checkpoint-drain rule (no schema migration while a live checkpoint references the old shape) applies.

## Acceptance Criteria

- [ ] THE committed snapshots SHALL capture the design/blog/slide/strategy/creator-asset JSON responses as byte-identical baselines (volatile normalized) with a diff helper
- [ ] THE FileResponse endpoints (pdf/images/slide-images/download) SHALL be asserted for identical content-type/headers + byte content (or stable digest) + artifact URL strings
- [ ] THE image-dependent paths SHALL use a DETERMINISTIC image-provider stub (no live provider; no API key) and pin env-sensitive settings for local/CI determinism
- [ ] EACH added presentation scenario SHALL be backed by an executing test (no orphan scenarios)
- [ ] WHEN `uv run pytest` runs THE safety-net suite SHALL pass with NO production code modified (green baseline recorded)

## Gherkin Scenarios

```gherkin
Feature: Presentation safety net (representative)

  Scenario: design response unchanged
    Given a rendered carousel
    When GET /api/carousels/{id}/design runs
    Then the response matches the committed snapshot

  Scenario: pdf bytes + headers unchanged
    Given a built carousel PDF
    When GET /api/carousels/{id}/pdf runs
    Then the content-type/headers and byte digest match the snapshot
```

## Delta

### ADDED

- tests/integration/test_presentation_safety_net.py
- tests/snapshots/presentation/* + diff helper
- presentation Gherkin scenarios

### MODIFIED

- tests/features/*carousel* presentation feature(s) (audit/extend)

### REMOVED

- None

## Affected Areas

- Backend: none
- Frontend: none
- Database: none (additive-only if any; no schema migration planned)
- API: none
- Tests: safety net + snapshots
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0118, AE-0120, AE-0121
- Blocked by: None
- Related: AE-0097, AE-0106, AE-0114

## Implementation Plan

1. Audit media/preview/strategies tests + test_media_access.py.
2. Snapshot JSON + FileResponse bytes/headers/URLs with a deterministic image stub; pin DEBUG.
3. Record green baseline; no src/ change.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created by planner (Phase 5 breakdown).

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
