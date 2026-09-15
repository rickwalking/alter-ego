# AE-0346 — finish the llm_json_retry rollout: empty re-roll everywhere, and an honest error contract

Status: Ready
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

Every agent that parses JSON out of an LLM survives the same failures the same
way, and `ainvoke_json` raises what its docstring says it raises.

## Problem

Found while QA-ing the merged AE-0330 work (2026-09-15). AE-0330 introduced
`agents/llm_json_retry.ainvoke_json` — empty reply → one re-roll, malformed reply
→ one repair round-trip — and adopted it in the outline and content agents. The
rollout is incomplete in four distinct ways:

1. **`source_synthesis_agent` has no empty-response re-roll.** It keeps its own
   AE-0318 `_parse_with_repair`, which handles *malformed* output but has **no
   empty branch**: an empty reply falls straight into the repair round-trip,
   which sends an empty `AIMessage` plus the repair prompt — repairing nothing,
   burning a call, and then failing. An empty reply is precisely the live failure
   AE-0330 was raised for (GLM 5.2 spending 31,999 of 32,000 tokens on
   reasoning), so this phase is still exposed to it. The external review recorded
   this agent as behaviourally equivalent to the new module; it is not.

2. **The declared error contract is not delivered.** `ainvoke_json`'s docstring
   says it raises `ValueError(ERR_INVALID_JSON)` after exhaustion. The final
   re-raise can be a **`TypeError`** — both `_parse_draft` and `_parse_outline`
   raise `TypeError` for valid JSON of the wrong shape — and
   `phase_artifact_runner` catches only `ValueError`. That path escapes as an
   unhandled exception and becomes a 500 on start.

3. **`cast(str, response.content)`** in `_ainvoke_once` and `_arequest_repair`
   asserts a type the LangChain contract does not guarantee: `AIMessage.content`
   is `str | list[...]`, and reasoning models can return content blocks. A list
   makes `raw.strip()` raise `AttributeError`, outside the declared contract
   entirely. Latent — not yet observed — but GLM 5.3 is a reasoning model.

4. **Two more call sites in the same defect class** still die on one bad sample:
   `application/services/carousel/editorial_distribution_generation.py:134` and
   `.../nodes/content/core.py:59`.

Separately, the AE-0330 test suite has a **cache-HIT gap**: the Gherkin scenario
"a response that parses is still served from cache without calling the model" has
no matching assertion for the outline/content agents — deleting their
`_cache.set` call would still pass. `source_synthesis` does cover it.

## Scope

- Move `source_synthesis_agent` onto `ainvoke_json` (deleting its duplicate
  `_parse_with_repair`), or add the empty re-roll to its own path — prefer the
  former so there is one implementation.
- Make the raised type match the documented contract: normalize the terminal
  failure to `ValueError(ERR_INVALID_JSON)` (chaining the original), **or** widen
  the `phase_artifact_runner` catch to the real surface and fix the docstring.
  Pick one and state why; do not leave the docstring lying.
- Replace the `cast(str, ...)` with a real normalization of
  `str | list[str | dict]` to text, with a test for the list-of-blocks shape.
- Adopt the shared helper at the two remaining call sites.
- Add cache-HIT tests for the outline and content agents (assert the model is
  **not** called on a hit).

## Non-Goals

- Changing the retry counts or adding a third attempt.
- Reworking the cache implementation.
- The `draft_text` typing defect (AE-0334) — different layer, already ticketed.

## Acceptance Criteria

- [ ] An empty reply in the source-synthesis phase triggers a re-roll and a
      successful second attempt — test drives empty-then-good.
- [ ] Two consecutive empty replies raise the documented error and cache nothing.
- [ ] A wrong-shape-but-valid JSON reply raises the type the docstring declares,
      and is handled (not a 500) — test drives it through `phase_artifact_runner`.
- [ ] `AIMessage.content` returned as a list of content blocks is handled, not
      an `AttributeError` — test covers the list shape.
- [ ] `editorial_distribution_generation.py` and `nodes/content/core.py` use the
      shared helper.
- [ ] Cache-HIT tests for outline and content assert the model is not called;
      removing `_cache.set` makes them fail.
- [ ] Only one JSON-retry implementation remains in `backend/src`.
- [ ] `bash scripts/ci/gate-capture.sh backend` green; GATES_JSON in the dev summary.

## Gherkin Scenarios

```gherkin
Feature: Every JSON-parsing agent survives the same failures

  Scenario: An empty reply during source synthesis is re-rolled
    Given the model returns empty content once, then valid JSON
    When source synthesis runs
    Then the synthesis succeeds
    And the model was called twice

  Scenario: Two empty replies fail cleanly
    Given the model returns empty content twice
    When source synthesis runs
    Then the documented JSON error is raised
    And nothing is written to the cache

  Scenario: Valid JSON of the wrong shape is handled
    Given the model returns a JSON array where an object is required
    When the content phase runs
    Then the phase reports a JSON failure
    And no unhandled exception reaches the API

  Scenario: Content returned as blocks is read correctly
    Given the model returns its content as a list of blocks
    When the reply is read
    Then the text is extracted without error

  Scenario: A cached response is served without calling the model
    Given a parseable cached response for the prompt
    When the outline agent runs
    Then the cached outline is returned
    And the model is not called
```

## Affected Areas

- Backend: `agents/llm_json_retry.py`, `agents/source_synthesis_agent.py`, `application/services/carousel/editorial_distribution_generation.py`, `application/services/carousel/nodes/content/core.py`, `application/services/carousel/phase_artifact_runner.py`
- Frontend: no
- Database: no
- API: error classification for the wrong-shape case
- Tests: unit tests for all four gaps plus the cache-HIT tests
- Docs: no
- Prompts/LLM: no prompt content change
- Observability: consistent retry logging across agents
- Deployment: no

## Dependencies

- Blocks: uniform LLM failure tolerance
- Blocked by: none
- Related: AE-0330 (introduced the module), AE-0318 (the original repair round-trip), AE-0334

## Implementation Plan

1. Failing tests for each of the four gaps.
2. Move source synthesis onto `ainvoke_json`; delete the duplicate.
3. Settle and implement the error contract; fix the docstring or the catch.
4. Normalize `content` to text; test the block-list shape.
5. Adopt the helper at the two remaining call sites.
6. Add the cache-HIT tests.

## QA Checklist

- [ ] Security reviewed (raw-response logging: consider trimming or redacting)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (empty, whitespace-only, wrong shape, block list)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Created from the retroactive QA of AE-0330 (see `.agent/reports/AE-0330.qa.md`).
Gap 1 was found by this session while checking the external reviewer's claim that
`source_synthesis` was already equivalent — it is not. Gaps 2 and 4 and the
cache-HIT gap were found by the external reviewer; gap 3 by this session.

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
