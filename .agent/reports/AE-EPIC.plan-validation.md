# Plan Validation — Slide Layout Strategy Pattern Epic (AE-0004 to AE-0007)

**Status:** WARN
**Validator:** architect-skill (validate mode)
**Date:** 2026-06-04

## Epic Overview

| Ticket | Area | Tier | Status |
|--------|------|------|--------|
| AE-0007 | Design (visual improvements) | T2 | Intake |
| AE-0005 | Backend API + DI Wiring | T2 | Intake |
| AE-0004 | Frontend Strategy Selector | T2 | Intake |
| AE-0006 | Strategy Tests | T2 | Intake |

Execution order: AE-0007 → AE-0005 → AE-0004 → AE-0006

---

## Checks by Area

### Structure (Goal, problem, scope, non-goals, dependencies)

| Ticket | Goal | Problem | Scope | Non-goals | Dependencies |
|--------|------|---------|-------|-----------|--------------|
| Architecture plan (§1-§11) | ✅ | ✅ | ✅ | ✅ | ✅ |
| AE-0007 | ✅ | ✅ | ✅ | ✅ | ✅ |
| AE-0005 | ✅ | ✅ | ✅ | ✅ | ✅ |
| AE-0004 | ✅ | ✅ | ✅ | ✅ | ✅ |
| AE-0006 | ✅ | ✅ | ✅ | ✅ | ✅ |

All present and well-structured.

### Acceptance Criteria Quality (EARS style)

| Ticket | AC Count | Specific? | Testable? | Issues |
|--------|----------|-----------|-----------|--------|
| AE-0007 | 6 | ✅ | ✅ | No numeric target for "verified visually" — suggest adding an HTML assertion |
| AE-0005 | 8 | ✅ | ✅ | AC for 409 refers to "non-completed project" — should specify which statuses map to this (e.g. `drafting`, `awaiting_human`) |
| AE-0004 | 7 | ✅ | ✅ | AC 6 ("highlights correctly after regenerate") is ambiguous — what exactly is "correctly"? |
| AE-0006 | 8 | ✅ | ✅ | AC 8 ("90%+ branch coverage on new code") — no guidance on which tool/method to measure |

**Suggested AC additions:**

- AE-0007 AC 7: "Slide 7 HTML does not contain `.slide-watermark` class"
- AE-0005 AC 9: "GET /api/carousels/{id} response includes `slide_layout_strategy` field (null when not set)"
- AE-0004 AC 8: "Loading state shown while regenerate mutation is in-flight"

### Gherkin Scenario Coverage

| Ticket | Scenarios | Happy Path | Failure Path | Edge Cases | Gaps |
|--------|-----------|------------|--------------|------------|------|
| Architecture plan (§6) | 10 | ✅ | ✅ (422) | ✅ | — |
| AE-0007 | 4 | ✅ | ❌ | ❌ | **No failure scenarios:** what if carousel has <7 slides (no slide 7)? What if slide data is empty? What about RTL language for swipe text? |
| AE-0005 | 4 | ✅ | ✅ (422, 409) | ✅ | — |
| AE-0004 | 4 | ✅ | ❌ | ❌ | **No failure scenarios:** what if GET /strategies times out? What if regenerate mutation fails (network error, 422)? No double-click guard scenario |
| AE-0006 | 9 | ✅ | ✅ (422) | ❌ | Missing: "No stats/features/insight" edge case (should render hero_content fallback) though architecture plan covers this |

**Gherkin gaps:**
- AE-0007: Add failure scenario for carousel with <7 slides
- AE-0007: Add edge case for empty/missing slide data
- AE-0004: Add failure scenario for network error on regenerate
- AE-0004: Add edge case for double-click/multiple rapid regenerates
- AE-0006: Add "empty slide data" fallback scenario

### Risks Assessment

| Risk Area | Covered in plan §9? | Covered in tickets? | Issue |
|-----------|--------------------|---------------------|-------|
| Missing structured data | ✅ | ✅ (AE-0006 tests) | — |
| Theme/strategy CSS conflict | ✅ | ❌ | Not explicitly tested — AC should cover visual regression check |
| Registry thread safety | ✅ | ✅ (AE-0006) | — |
| Strategy name collision | ✅ | ✅ (AE-0006) | — |
| Frontend/backend version mismatch | ✅ | ❌ | Not tested — edge case note in ticket would help |
| **Database migration rollback** | ❌ | ❌ | AE-0005 adds a column with no rollback plan in ticket → **WARN** |
| Slide data `features`/`stats`/`insight` missing after pipeline change | ✅ | ✅ (AE-0006 fallback tests) | — |

### Edge Cases

| Ticket | Timeouts | Idempotency | Empty State | Permissions | Issue |
|--------|----------|-------------|-------------|-------------|-------|
| AE-0007 | ❌ | N/A (pure render) | ❌ | N/A | No handling for 0 slides or slide 7 not existing |
| AE-0005 | ❌ | ❌ | ✅ (404) | ❌ | No timeout for regeneration (could be slow if many slides) |
| AE-0004 | ❌ | ✅ | ❌ | ❌ | No loading/error state for strategy list fetch |
| AE-0006 | N/A | N/A | ✅ (empty data) | N/A | — |

### ADR Fit Check

| ADR | Relevance | Conflict? |
|-----|-----------|-----------|
| ADR-007 (Consolidate Carousel Under DeepAgents) | **Rendering layer**, not AI orchestration | ✅ **No conflict** — strategies are pure HTML/CSS renderers, not agent workflows. They live in `application/services/carousel_template/`, which is the output rendering layer, separate from the DeepAgents editorial pipeline |
| ADR-002 (LangGraph) | Strategy registry uses simple dict, not LangGraph | ✅ No conflict — strategies are deterministic rendering, not workflow |
| ADR-003 (Persona Engine) | Not affected | ✅ |
| ADR-004 (Event-Driven) | Not affected | ✅ |
| ADR-005 (Mutation Testing) | Referenced in AE-0006 (not yet applicable) | ✅ Waived per CLAUDE.md (mutation testing is "weeks away") |
| ADR-006 (JSONB) | Slide data already stored as JSONB | ✅ Strategies consume JSONB fields via `SlideDict` — no change |

### High Risk Areas from config.yaml

| Area | Touched by | Risk Level | Mitigation |
|------|-----------|------------|------------|
| `database_migrations` | AE-0005 (new column) | **Medium** | Add-only migration (nullable column, no backfill needed). Add rollback step to ticket |
| `authentication` | None | Low | — |
| `authorization` | None | Low | — |
| `langgraph_workflow_state` | None | Low | — |
| `prompts` | None | Low | — |
| `llm_provider_changes` | None | Low | — |
| `publishing` | AE-0005 (regenerate endpoint could be called on published carousels) | **Low** | Would re-render slides for a published project; should this be allowed? Not documented |

### Testing Coverage (per ADR-005)

| Layer | Covered By | Status |
|-------|-----------|--------|
| Unit — Protocol interface | AE-0006 test_strategy_interface.py | ✅ |
| Unit — Per strategy | AE-0006 (4 strategy-specific test files) | ✅ |
| Unit — Registry | AE-0006 test_registry.py | ✅ |
| Integration — API | AE-0006 test_strategy_endpoints.py | ⏳ Blocked by AE-0005 |
| Property — Hypothesis | AE-0006 test_strategy_properties.py | ✅ |
| Gherkin feature file | AE-0006 | ⏳ Not yet created |

---

## Summary by Ticket

### AE-0007 — PASS with suggested improvements
- Strong AC, clear scope, independent dependency chain
- Missing: failure Gherkin scenarios, <7 slides edge case

### AE-0005 — WARN
- Database migration needs rollback plan documented
- No timeout specification for regenerate endpoint
- Should clarify whether regenerate works on published carousels
- Otherwise well-structured with testable AC and good Gherkin coverage

### AE-0004 — PASS with suggested improvements
- Clean scope, clear AC
- Missing: network failure edge cases, double-click guard

### AE-0006 — PASS
- Comprehensive test plan covering unit, integration, property, and Gherkin
- Integration tests correctly blocked by AE-0005

---

## Blocking Gaps (FAIL)

None. All tickets are structurally sound.

## Warnings

1. **AE-0005: Missing DB migration rollback plan** — Add a rollback step to the implementation plan (e.g. `ALTER TABLE carousel_projects DROP COLUMN slide_layout_strategy;`)
2. **AE-0007: No failure-path Gherkin** — Add at least one failure scenario for <7 slides
3. **AE-0004: No network error Gherkin** — Add failure scenario for regenerate/strategy fetch
4. **AE-0005: Published carousel edge case** — Should regenerate be allowed on published projects? If yes, should it auto-unpublish?

## Suggested AC Additions

- AE-0007 AC 7: Slide 7 HTML does not contain `.slide-watermark` class
- AE-0007 AC 8: Carousel with <7 slides gracefully ignores hero-bg layout on last slide
- AE-0005 AC 9: Migration is reversible (`ALTER ... DROP COLUMN`)
- AE-0004 AC 8: Loading state shown while regenerate mutation is in-flight
- AE-0004 AC 9: Error toast shown if regenerate fails

## Verdict

**Overall: PASS with 4 warnings.** The epic is well-architected, the tickets are well-structured, and the ADR fit is clean. The warnings are non-blocking and can be resolved incrementally as each ticket is implemented.

**Ready for development after resolving:**
1. Add rollback step to AE-0005 implementation plan
2. Add <7 slides edge case to AE-0007 Gherkin
3. Add network error Gherkin to AE-0004
4. Clarify published carousel policy in AE-0005

**Recommended order:** AE-0007 → AE-0005 → AE-0004 → AE-0006 ✅ (already documented in plan)
