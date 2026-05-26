# ADR-005: Adopt Mutation Testing for Code Quality

## Status

Accepted

## Context

The project already targets 90%+ line/branch coverage. However, coverage alone doesn't guarantee tests assert correct behavior — a test can execute code without checking results. We need to measure test quality, not just test quantity.

## Decision

Adopt **mutation testing** as a complementary quality metric:
- **Backend (Python):** `mutmut` with weekly CI runs
- **Frontend (TypeScript):** `StrykerJS` with incremental PR checks (after baseline)

## Decision Drivers

- High coverage but weak assertions is a known risk
- Mutation testing finds weak assertions that coverage misses
- We need confidence that refactors don't break behavior
- Industry standard for quality-conscious teams

## Considered Options

### Option 1: Property-Based Testing Only (Hypothesis, fast-check)

- **Good:** Finds edge cases automatically
- **Bad:** Different concern — finds bugs in code, not weakness in tests
- **Verdict:** Rejected — complementary but not a substitute

### Option 2: Higher Coverage Thresholds (95%, 100%)

- **Good:** Simple to enforce
- **Bad:** Doesn't solve the weak assertion problem; encourages trivial tests
- **Verdict:** Rejected — treats symptom, not cause

### Option 3: Mutation Testing

- **Good:** Directly measures assertion strength; finds holes in test logic
- **Bad:** Slow (10-100x slower than unit tests); requires interpretation
- **Verdict:** Accepted — best measure of test quality

## Consequences

**Good:**
- Tests must actually assert behavior, not just execute code
- Catches subtle logic bugs that coverage misses
- Drives better test design (boundary values, equivalence classes)

**Bad:**
- Slower CI — mutation tests run nightly, not per-PR (initially)
- Some mutants are "equivalent" (no test can kill them) — creates noise
- Requires team education on interpreting results
- ~20-30% increase in test development time initially

## Implementation Plan

### Phase 1: Baseline (Week 1)
- Install mutmut and StrykerJS
- Run full mutation test to establish baseline score
- Document current score and top surviving mutants

### Phase 2: Critical Modules (Weeks 2-4)
- Focus mutation testing on:
  - `chat_stream_service.py`
  - `carousel_orchestrator`
  - `use-sse-chat.ts`
  - `use-publish-chat.ts`
- Target: 70%+ mutation score on critical modules

### Phase 3: Full Suite (Weeks 5-8)
- Expand to all business logic
- Target: 70%+ overall mutation score

### Phase 4: CI Integration (Week 9+)
- Backend: Weekly scheduled run on GitHub Actions
- Frontend: Incremental Stryker on PRs (after 80%+ baseline)

## Thresholds

| Module Type | Break | Low | High |
|-------------|-------|-----|------|
| Business Logic | 50% | 70% | 80% |
| API Routes | 40% | 60% | 75% |
| UI Components | 30% | 50% | 65% |

## Related Decisions

- ADR-001: Adopt MADR for Architecture Decision Records

## Tags

#testing #quality #mutation-testing #process
