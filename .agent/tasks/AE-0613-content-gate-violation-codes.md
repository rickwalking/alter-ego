# AE-0613 — Content gate records its violation codes in the event details

Status: In Development
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

- [x] AC1 Given a blocked gate, When its artifacts are recorded, Then the event stores the codes of the rules that fired.
- [x] AC2 Given a passing gate, When its artifacts are recorded, Then the event has no `violation_codes` key and is not marked truncated.
- [x] AC3 Given a violation with a message and slide text, When stored and read, Then the row and the API response hold the code only.
- [x] AC4 Given an unknown or free-text code, When recorded, Then it is dropped and the event is marked truncated.
- [x] AC5 Given many codes, When sanitized, Then the value survives within the bounds, blockers first, and the event is marked truncated.
- [x] AC6 Given a non-allowlisted key or an oversized or unsafe `violation_codes` value, When sanitized, Then it is dropped and marked truncated.
- [x] AC7 Given a dropped blocker and a warning that would fit, When recorded, Then only blockers are stored, sorted, and the event is marked truncated.

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

Review round 1: a test with the review's exact example failed on the old code, along with four cases of a blocker dropped
for an unknown code or a malformed entry. A warning is now stored only when no blocker was dropped. The new tests cover
that rule, the known set against the sanitizer, and the `truncated` key against the sanitizer's literal.

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

- Red: with the allowlist key and the `_record_gate` wiring removed, 18 of the 34 new tests failed.
- Green: 60 passed across the new unit and integration tests and the AE-0556 unit and integration tests.
- `diff-cover` on the touched tests: 100% (54 lines, 0 missing).
- Single backend gates PASS: format, lint, lint-diff, blanket-ignore, strict-diff, type, imports, arch-ratchet,
  docstrings, dead-code, inline-prompts, gherkin-refs, comments, blog-v1-dead-code, redis-factory, autopilot-env,
  healthcheck-loopback, openapi-fresh, bandit, pip-audit, integrity, duplication, migrations, schema-drift.
- Review round 1 red: 5 of the new tests failed on the old builder (the review's example and 4 dropped-blocker cases).
- Review round 1 green: 92 passed across the AE-0613 and AE-0556 unit and integration tests (Postgres `DATABASE_URL`).
  `diff-cover` on those tests: 100% (61 lines, 0 missing).
- Review round 1 single gates PASS: format, lint, lint-diff, blanket-ignore, strict-diff, type, imports, arch-ratchet,
  comments, gherkin-refs, dead-code, docstrings, diff-cover.
- Full gate: lead's heavy slot. Mutation: CI only (AE-0448).

## QA Report

Pending.

## Decision Log

- 2026-11-04 (Pedro): exactly one new key, `violation_codes`; no other sanitizer change.
- 2026-11-04: one string joined by `.`, not a count per code. Comma and space fail `_SAFE_CODE`; no known code holds a `.`.
- 2026-11-04: the real cap is 64 characters, not the 120 of `_EVENT_STRING_MAX_CHARS`, because the value passes through
  `_SAFE_CODE`. That holds between 2 and about 5 codes, so the length budget is the count cap. Raising it would need a
  sanitizer change that Pedro's decision rules out.
- 2026-11-04: when space runs out, blockers are kept ahead of warnings, because the production question is which rule
  blocked. The stored value is still sorted. A shorter code may fill room a longer one could not use, with one limit
  (next entry).
- 2026-11-04 (review): a warning is stored only when no blocker was dropped. Before this, a long blocker that did not fit
  was skipped and a shorter warning could take its place: blockers A, B, long C and warning `markup_leak` stored
  `A.B.markup_leak`, which reads as if `markup_leak` blocked. Now any dropped blocker leaves blockers only, still sorted
  and still `truncated: true`. A blocker dropped for an unknown code or a malformed entry counts too; an entry with no
  readable severity counts as a blocker, as the violation model defaults. No new key and no sanitizer change.
- 2026-11-04 (review): the value still does not say which code is a blocker. With every blocker stored, a stored warning
  sits next to them unmarked, and `truncated` does not say what was dropped. Marking that would need a new key or a
  value format change, which is out of scope here.
- 2026-11-04 (review): the known set now has a test that each code is `[a-z0-9_]+` and survives the sanitizer, so a
  `VIOLATION_*` constant that is not a rule id fails a test. The check uses `sanitize_event_details` rather than the
  private `_SAFE_CODE`.
- 2026-11-04 (review): `DETAIL_TRUNCATED` repeats the sanitizer's literal because the sanitizer has no constant to import
  and adding one is a sanitizer change Pedro's decision rules out. A test ties the two together.
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
