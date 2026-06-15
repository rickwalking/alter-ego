# AE-0126 — modules/publishing skeleton + facade + domain (BlogPost/Publication/DistributionChannel/PublishingSchedule) + ports

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0126-publishing-module
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Create modules/publishing/ (domain/application/infrastructure/api + public.py + bootstrap.py + constants.py) mirroring modules/editorial+presentation; define publishing domain (BlogPost aggregate, Publication carousel-projection view, DistributionChannel, PublishingSchedule) + re-export BlogPost/Carousel repo ports via object-identity shims. No routes/migration moved yet.

## Problem

There is no publishing module today; the skeleton + domain + facade must exist before the migration (AE-0127), persistence/distribution/outbox (AE-0128/0129/0130), and projections (AE-0131).

## Scope

- Scaffold modules/publishing per conventions + the editorial/presentation pattern (public.py facade + bootstrap.py manual DI, no get_container).
- Define publishing domain entities/value objects: BlogPost aggregate (over blog_posts), Publication (carousel→blog read projection view), DistributionChannel, PublishingSchedule, ReleaseState — fully typed (no Any).
- Re-export the BlogPost + Carousel repository ports + relevant entities via object-identity shims (existing callers unbroken); reuse the platform UoW.
- Add a smoke test proving public symbols import + a re-export is object-identical.

## Non-Goals

- No routes/migration/outbox moved (AE-0127..0131).
- No publish behavior change.
- No distribution extraction yet.

## Modularization Alignment (2026-06-15)

Phase 6 of the modularization plan (§Phase 6). **Behavior-preserving + additive-only** for the IN scope — blog/publish/distribution/calendar/board/analytics responses + the public carousel /blog stay byte-identical; the migration is ADDITIVE (add origin + backfill; NO column drop); the outbox is ADDITIVE (alongside the existing after-commit publish); NO renames. The auto-publish behavior cutover + the destructive embedded-column drop are DEFERRED (documented follow-up; the approval≠release contract is already split in AE-0111). Follow `docs/architecture/module-conventions.md` + the modules/editorial+presentation pattern; reuse the platform UoW, the QA-guardian gates, and the AE-0103/0112/0122 import-contract + ratchet pattern; compose via DI at the edge (no get_container in module code). publishing is invoked BY editorial/presentation via the facade (acyclic; publishing imports no editorial/presentation internals). Precondition: Phase 5 (PR #19) merged. The checkpoint-drain rule applies to any schema-modifying migration (Phase 6's is additive ⇒ no drain needed).

## Acceptance Criteria

- [ ] modules/publishing SHALL exist per conventions with public.py facade + bootstrap.py (manual DI, no get_container)
- [ ] BlogPost/Publication/DistributionChannel/PublishingSchedule SHALL be typed (no Any) and re-export existing blog/carousel types via object-identity shims (no new domain strings)
- [ ] THE BlogPost + Carousel repository ports SHALL be re-exported (existing callers keep resolving; CI-verified)
- [ ] THE module SHALL reuse the platform/database UoW (no new UoW)
- [ ] WHEN mypy/lint-imports/pytest run THEY SHALL pass with no new violations and no behavior change

## Gherkin Scenarios

Not applicable — behavior-preserving scaffolding; verified by mypy/lint-imports + the AE-0125 safety net.

## Delta

### ADDED

- modules/publishing/{domain,application,infrastructure,api}/, public.py, bootstrap.py, constants.py
- publishing domain entities
- tests/unit/modules/publishing/*

### MODIFIED

- None (re-export only)

### REMOVED

- None

## Affected Areas

- Backend: publishing module
- Frontend: none (Phase 7)
- Database: none (additive-only if any)
- API: none yet
- Tests: contract/behavior tests
- Docs: references conventions
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0127, AE-0128, AE-0129, AE-0130, AE-0131, AE-0132
- Blocked by: None
- Related: AE-0108, AE-0117, AE-0123

## Implementation Plan

1. Scaffold modules/publishing from the editorial/presentation pattern.
2. Define domain + re-export blog/carousel ports.
3. Bootstrap; mypy/lint-imports/smoke test.

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
