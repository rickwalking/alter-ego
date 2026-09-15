# AE-0334 — type draft_text in the content prompt and reject a nested draft object

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

Make a malformed `draft_text` from the LLM a **loud, retryable parse failure**
instead of silently becoming a stringified Python dict or an empty slide body.

## Problem

Observed live on carousel `dcaa5fef-9d91-4ab1-80b2-e77860ab8a43` (2026-09-15):
GLM returned a **nested object** for `draft_text` on **12 of 13** drafts. Three
layers each failed to catch it:

1. **The prompt does not type the field.** The v4 content prompt asks for
   `draft_text` without stating it must be a plain string, so a reasoning model
   happily returns `{"heading": ..., "body": ...}`.
2. **`_parse_draft` coerces instead of validating.**
   `backend/src/rag_backend/agents/content_draft_agent.py:178`:

   ```python
   "draft_text": str(data.get("draft_text", "")),
   ```

   `str()` on a dict succeeds — it produces `"{'heading': '...', 'body': '...'}"`.
   The function validates the *top-level* payload is a dict (line 174) but never
   checks the type of `draft_text` itself, so no `ValueError` is raised and the
   retry path never fires.
3. **The sanitizer then overwrites it from a different source.**
   `application/services/carousel/workflow_state_sanitize.py:185`:

   ```python
   updated[_DRAFT_TEXT_KEY] = str(pt_body.get("body") or "")
   ```

   so `draft_text` becomes the `presentation_pt.body` — which at that point is
   either stale text from a previous pass or **empty**. An empty body is not
   treated as blocking anywhere, so the run proceeds with blank copy.

The last run was only rescued by an unrelated fail-closed retry-draft that
happened to regenerate the final slide. The defect is fully live.

## Scope

- The v4 content prompt (`agents/prompts/carousel/v4/content_prompt.yaml` or the
  current default version): state explicitly that `draft_text` is a **plain
  string**, with a worked example. Per the prompt-versioning rule, create a new
  version folder rather than editing the existing one if the default is in use.
- `content_draft_agent._parse_draft`: reject a non-`str` `draft_text` with
  `ValueError(ERR_INVALID_JSON)` so the AE-0330 `llm_json_retry` repair path
  engages (malformed → `JSON_REPAIR_PROMPT`).
- `workflow_state_sanitize`: do not overwrite a **non-empty** `draft_text` from
  `presentation_pt.body`; and make an empty resulting body blocking rather than
  silently acceptable.
- A validation rule that a completed content phase has no empty slide body.

## Non-Goals

- Changing the LLM provider or model (GLM 5.3 stays).
- Rewriting the whole draft schema to Pydantic — type-checking this one field and
  the empty-body guard is the fix. A broader schema pass can follow.
- Re-running the dcaa5fef carousel (it is completed and approved).

## Acceptance Criteria

- [ ] `_parse_draft` raises `ValueError(ERR_INVALID_JSON)` when `draft_text` is a
      dict, list, number, or `None` — unit-tested for each type.
- [ ] A malformed `draft_text` triggers the `llm_json_retry` repair path, and a
      second malformed reply fails the phase loudly (no silent empty slide).
- [ ] The content prompt states the `draft_text` type and shows a valid example;
      a new prompt version folder is created if the current one is the default.
- [ ] `workflow_state_sanitize` leaves a non-empty `draft_text` untouched and
      only falls back to `presentation_pt.body` when `draft_text` is absent.
- [ ] A content phase that would finish with any empty slide body fails the
      phase instead of completing.
- [ ] Regression test reproducing the nested-object payload from the dcaa5fef run.

## Gherkin Scenarios

```gherkin
Feature: Content draft parsing rejects malformed draft_text

  Scenario: The model returns a nested object for draft_text
    Given the content agent receives {"draft_text": {"heading": "H", "body": "B"}}
    When the draft is parsed
    Then a JSON validation error is raised
    And the JSON repair retry is attempted

  Scenario: The repair also fails
    Given the repair reply is also malformed
    When the content phase runs
    Then the phase fails with an explicit reason
    And no slide is stored with a stringified dict as its body

  Scenario: A good draft is not overwritten by the sanitizer
    Given draft_text is a non-empty string
    And presentation_pt.body is empty
    When the state is sanitized
    Then draft_text keeps its original value

  Scenario: An empty slide body blocks completion
    Given one slide would finish with an empty body
    When the content phase tries to complete
    Then the phase fails instead of completing
```

## Affected Areas

- Backend: `agents/content_draft_agent.py`, `application/services/carousel/workflow_state_sanitize.py`
- Frontend: no
- Database: no
- API: no
- Tests: unit + regression for the nested-object payload
- Docs: prompt version README
- Prompts/LLM: yes — content prompt typing (new version folder)
- Observability: log the rejected payload shape
- Deployment: no

## Dependencies

- Blocks: trustworthy carousel content output
- Blocked by: none
- Related: AE-0330 (`llm_json_retry`), AE-0335 (feedback never cleared), carousel defect wave AE-0334..AE-0339

## Implementation Plan

1. Add failing unit tests for each malformed `draft_text` type.
2. Type-check the field in `_parse_draft`; confirm the retry path engages.
3. Add the new prompt version with the typed field + example; point the default at it.
4. Fix the sanitizer overwrite; add the empty-body blocking rule.
5. Add the dcaa5fef regression fixture.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (dict, list, int, None, empty string)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Ticket created from the AE-0330 session handoff (defect #7). Confirmed live at
`content_draft_agent.py:178` and `workflow_state_sanitize.py:185`.

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
