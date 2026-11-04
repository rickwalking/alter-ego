# AE-0613 — Content gate records its violation codes in the event details

Status: In Progress
Tier: T2
Priority: Medium
Type: Feature
Area: Backend
Owner: Claude
Agent Lane: developer → qa → release
Branch: feat/ae-0613-content-gate-violation-codes
Kanban Card: TBD
Created: 2026-11-04
Updated: 2026-11-04

## Goal

A `content_gate` generation event records which presentation rules fired, as rule ids from the existing violation
constants (for example `heading_not_sentence_case_en`). It never records a message, slide text, field value or
anything user-written.

## Problem

Pedro's decision (2026-11-04): a production check could not tell which rule a content gate blocked or passed on,
because the event stores only `violation_count` and `blocking_count`.

## Scope

- Add exactly one key, `violation_codes`, to `_ALLOWED_DETAIL_KEYS`. That is the only sanitizer change.
- Build the value only from the known violation constants: map, keep known codes, de-duplicate, cap, sort, join.
- Mark any omission with the existing `truncated` detail.

## Non-Goals

- No change to the gate's decisions, any validator, limit, threshold or severity.
- No other detail key, raised limit, loosened `_SAFE_CODE` or other sanitizer change.
- No migration (details is JSON). No frontend work; the API already returns details as a string-keyed record.

## Acceptance Criteria

- [ ] AC1 Given a blocked gate, When its artifacts are recorded, Then the event stores the codes of the rules that fired.
- [ ] AC2 Given a passing gate, When its artifacts are recorded, Then the event has no `violation_codes` key and is not marked truncated.
- [ ] AC3 Given a violation with a message and slide text, When stored and read, Then the row and the API response hold the code only.
- [ ] AC4 Given an unknown or free-text code, When recorded, Then it is dropped and the event is marked truncated.
- [ ] AC5 Given many codes, When sanitized, Then the value survives within the bounds, blockers first, and the event is marked truncated.
- [ ] AC6 Given a non-allowlisted key or an oversized or unsafe `violation_codes` value, When sanitized, Then it is dropped and marked truncated.

## Gherkin Scenarios

- `backend/tests/features/content_gate_violation_codes_ae0613.feature`

## Delta

### ADDED

- `domain/constants/violation_codes.py`: the known set, derived from the `VIOLATION_*` constants.
- `generation_queue/application/content_gate_codes.py`: the bounded detail builder.

### MODIFIED

- `content_gate` event details gain `violation_codes` when any rule fired.
- `_ALLOWED_DETAIL_KEYS` gains `violation_codes`.

### REMOVED

- None.

## Affected Areas

- Backend: generation queue event details.
- Frontend: none.
- Database: none (details is JSON).
- API: `details` of a `content_gate` event may hold `violation_codes`; the schema is unchanged.
- Tests: unit and SQLite integration, plus the new Gherkin feature.
- Docs: this ticket.
- Prompts/LLM: none.
- Observability: a production check can read which rules fired.
- Deployment: none.

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: AE-0556 (privacy contract for generation events).

## Implementation Plan

1. Write the Gherkin and failing tests.
2. Add the known set, the builder and the single allowlist key.
3. Run the touched tests and the cheap gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-04

Ticket and Gherkin written first. With the allowlist key and the wiring removed, 18 of the 34 new tests failed; with both
in place all 34 pass, plus the existing AE-0556 unit and integration tests.

## Files Touched

- `backend/src/rag_backend/domain/constants/violation_codes.py` (new)
- `backend/src/rag_backend/modules/generation_queue/application/content_gate_codes.py` (new)
- `backend/src/rag_backend/modules/generation_queue/application/generation_log_steps.py`
- `backend/src/rag_backend/modules/generation_queue/constants.py`
- `backend/src/rag_backend/modules/generation_queue/domain/generation_events.py` (one allowlist line)
- `backend/tests/features/content_gate_violation_codes_ae0613.feature` (new)
- `backend/tests/unit/modules/generation_queue/test_content_gate_violation_codes_ae0613.py` (new)
- `backend/tests/integration/test_content_gate_violation_codes_ae0613.py` (new)

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-11-04 (Pedro): exactly one new key, `violation_codes`; no other sanitizer change.
- 2026-11-04: one string joined by `.`, not a count per code. Comma and space fail `_SAFE_CODE`; no known code holds a `.`.
- 2026-11-04: the real cap is 64 characters, not the 120 of `_EVENT_STRING_MAX_CHARS`, because the value passes through
  `_SAFE_CODE`. That holds between 2 and about 5 codes, so the length budget is the count cap. Raising it would need a
  sanitizer change that Pedro's decision rules out.
- 2026-11-04: when space runs out, blockers are kept ahead of warnings, because the production question is which rule
  blocked. The stored value is still sorted. A shorter code may fill room a longer one could not use.
- 2026-11-04: any code not stored sets the existing `truncated` detail, so a partial list never reads as complete. This
  follows the sanitizer's "mark every omission" contract and adds no key.
- 2026-11-04: a passing gate omits the key. The sanitizer treats an empty string as an omission and would mark it truncated.
- 2026-11-04: the known set is derived from the `VIOLATION_*` constants in `carousel_presentation`, `presentation_roles`
  and `playwright_geometry`, so a new rule is not silently dropped. A test holds every contract rule inside the set.
- 2026-11-04: the integration test captures the event and writes it through the SQL recorder directly, so it does not race
  the 100 ms best-effort budget. It adds its own file because PR #354 is changing the AE-0556 integration tests.

## Blockers

None.

## Final Summary

Pending.
