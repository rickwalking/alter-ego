# AE-0318 — source synthesis hardening cache after parse json repair retry and observable workflow start failures

Status: Ready
Tier: T1
Priority: High
Type: Bugfix
Area: backend
Owner: Unassigned
Branch: feat/ae-0317-0318-research-enrichment
Created: 2026-07-17
Updated: 2026-07-17

## Goal

A malformed/truncated LLM response during source synthesis self-heals (one JSON
repair retry) instead of self-poisoning (bad raw cached for 1h), and a failed
`workflow/start` is observable (logged, specific error detail) instead of a
silent generic 400.

## Problem

Prod incident 2026-07-17 (project f9e3e199, Langfuse traces 1a9d3a8c…/375358d6…):
GLM 5.2's streamed response for one source was truncated mid-JSON (~30s, no usage
frame recorded). Three defects compounded:

1. **Cache poisoning** — `SourceSynthesisAgent.extract_key_points` caches the raw
   response BEFORE parsing (`agents/source_synthesis_agent.py:52`), so truncated
   garbage was cached (TTL 1h, global scope) and the user's retry failed
   instantly on the poisoned entry.
2. **No repair retry** — `_parse_response` uses bare `extract_json`;
   `extract_json_with_repair` (one bounded LLM repair round-trip,
   `infrastructure/llm/json_utils.py:84-120`) exists and is battle-tested in the
   content drafter, but is not used here.
3. **Silent failure** — the route maps any `ValueError` to
   `400 {"detail": "Invalid request"}` with `from None` and NO logging
   (`api/routes/carousels/editorial_workflow.py:178-182`), which cost the entire
   diagnosis chain (prod logs showed only a bare 400).

## Scope

- `SourceSynthesisAgent.extract_key_points`: cache only AFTER a successful parse;
  on cache hit, a parse failure evicts the entry and falls through to a fresh LLM
  call (recovers pre-fix poisoned caches without redeploy/restart).
- Parse via the existing repair path (`extract_json_with_repair` or an equivalent
  seam accepting the agent's `BaseChatModel`; keep the ≤3-arg rule with a config
  object if threading is needed). Repair failure still raises `ValueError`
  (fail-closed, no fabricated findings).
- `workflow/start` route: log the swallowed exception (`workflow_start_failed`,
  structlog, project_id + error) and return the new specific detail constant
  `ERR_RESEARCH_SYNTHESIS_FAILED` (`domain/constants/carousel_workflow.py`)
  instead of `ERR_INVALID_REQUEST` for synthesis failures. Status stays 400.
- Regression tests for all three defects (Gherkin-first).

## Non-Goals

- Do not refactor unrelated code.
- No scraping/search changes (AE-0317).
- No change to cache TTL/scoping (CACHE-001 stays).
- No transport-level retry of the provider stream truncation.
- No frontend change (it surfaces `detail` verbatim).

## Acceptance Criteria

- [ ] A raw LLM response that fails JSON parsing is NEVER written to the AI
      response cache.
- [ ] A cached entry that fails parsing is evicted and a fresh LLM call is made.
- [ ] On first-parse failure, exactly one repair round-trip runs; repair success
      → synthesis succeeds and the good raw is cached.
- [ ] Repair failure → `ValueError` propagates; route returns 400 with detail
      `ERR_RESEARCH_SYNTHESIS_FAILED` and emits `workflow_start_failed`
      structlog error with project_id.
- [ ] Valid-JSON behavior unchanged (single LLM call, cached, parsed).
- [ ] `tests/features/source_synthesis_hardening.feature` covers happy,
      repair-success, repair-failure, poisoning regression, eviction.

## Gherkin Scenarios

```gherkin
Feature: Source synthesis is resilient to malformed LLM responses

  Scenario: Valid response is parsed and cached
    Given the LLM returns valid key-points JSON for a source
    When key points are extracted
    Then the findings are returned
    And the response is cached for reuse

  Scenario: Truncated response triggers one repair retry
    Given the LLM returns JSON truncated mid-string
    And the repair call returns the corrected JSON
    When key points are extracted
    Then the findings from the repaired JSON are returned
    And the malformed raw response is not cached

  Scenario: Repair failure fails closed with an observable error
    Given the LLM returns malformed JSON
    And the repair call also returns malformed JSON
    When the editorial workflow is started
    Then the response is 400 with the research synthesis failed detail
    And a workflow_start_failed error is logged with the project id

  Scenario: Retry after a transient malformed response is not poisoned
    Given a first extraction attempt failed on malformed JSON
    When the same source is extracted again
    Then a fresh LLM call is made
    And a valid response this time yields findings

  Scenario: Poisoned cache entry from a previous deploy is evicted
    Given the cache contains an unparseable raw response for a source prompt
    When key points are extracted for that source
    Then the poisoned entry is evicted
    And a fresh LLM call is made
```

## Repro Steps

1. Start the editorial workflow with any payload while the LLM returns a
   truncated JSON stream for one source (observed live: Langfuse obs
   `30d7e75626070ebb`, output ends mid-string, usage 0/0).
2. Observe `400 {"detail": "Invalid request"}` with nothing in backend logs.
3. Retry the same payload within 1h → instant 400 (poisoned cache replay).

## Affected Areas

- [x] Backend (agents, route error mapping, cache additive `delete` if needed)
- [ ] Frontend
- [x] Tests (feature + unit + route regression)

## Dependencies

- Related: AE-0317 (same branch/PR; this ships first in commit order).

## Progress Log

### 2026-07-17

Ticket created from `.agent/reports/AE-0317.arch-plan.md` §4.5; root cause fully
evidenced via prod Langfuse traces.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Fail-closed retained: repair failure still 400s (no fabricated findings); fix
  targets observability + self-healing, not silent success.
- Detail string change deemed additive (same status, same schema).

## Blockers

None.
