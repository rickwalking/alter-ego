# AE-0400 — A slide draft written as a fenced JSON object shows raw JSON on the slide

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: backend
Owner: Claude (owner-reported hotfix)
Agent Lane: developer → qa → release
Branch: fix/ae-0400-fenced-draft-blob
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

A slide draft that the model wrote as its bilingual JSON object, with or without a Markdown code fence, becomes the slide's copy. It never shows as raw JSON.

## Problem

Owner report, prod 2026-10-16 (carousel 98a2e2f0, autopilot run b241ded5): slide 3 showed a JSON blob. The model answered the draft as a ```` ```json ```` fenced `{pt:{heading,body}, en:{heading,body}}` object. `parse_bilingual_draft_blob` only recognised text starting with `{` and parsed it with `ast.literal_eval`. Because of the fence, normalization skipped the slide, and the raw JSON became `draft_text` and the localized PT body. The PT body was also auto-capitalized to "```Json", which tripped the `body_not_sentence_case_pt` content-gate blocker and escalated the run.

## Scope

- New `application/services/carousel/draft_blob_text.py`: `strip_code_fence`, `looks_like_object`, and `parse_object_text` (JSON first, Python-literal fallback).
- `malformed_draft_normalizer.parse_bilingual_draft_blob` and `_has_valid_presentations` use it.
- `visible_copy_sanitize._parse_stringified_mapping` uses it.

## Non-Goals

- Changing the drafting prompt (prompt files are versioned).

## Acceptance Criteria

- [x] AC1: A ```` ```json ```` fenced bilingual draft is normalized: `draft_text` is the PT body, and each locale's presentation has its own heading and body.
- [x] AC2: A fence without a language tag is read.
- [x] AC3: JSON `true`/`false`/`null` parse.
- [x] AC4: Plain copy and broken objects are left unchanged.
- [x] AC5: A fenced stringified locale blob resolves to the requested locale.

## Gherkin Scenarios

`backend/tests/features/fenced_draft_blob_ae0400.feature` (6 scenarios).

## Delta

### ADDED

- `backend/src/rag_backend/application/services/carousel/draft_blob_text.py`
- `backend/tests/features/fenced_draft_blob_ae0400.feature`
- `backend/tests/unit/application/test_fenced_draft_blob_ae0400.py`

### MODIFIED

- `backend/src/rag_backend/application/services/carousel/malformed_draft_normalizer.py`
- `backend/src/rag_backend/application/services/carousel/visible_copy_sanitize.py`

### REMOVED

- None.

## Affected Areas

- Backend: slide draft normalization
- Frontend: none
- Database: none
- API: none
- Tests: unit + feature
- Docs: this ticket
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0366, AE-0399

## Implementation Plan

1. Fence-aware object parser.
2. Use it in both blob parsers.
3. Tests and feature.

## QA Checklist

- [x] Security reviewed (parsing only; `json.loads` / `ast.literal_eval`, no eval)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-16

Owner reported slide 3. The prod checkpoint was fixed by hand (slide 3 unfenced, localized slide rebuilt, EN taken from the model's own blob). The code fix is this ticket.

## Files Touched

See Delta.

## Test Evidence

- `test_fenced_draft_blob_ae0400.py`: 8 passed; unit suite: 3985 passed.

## QA Report

Pending (hotfix fast path: CI Test & Coverage decides).

## Decision Log

- 2026-10-16: Fix at the shared parser so every consumer (normalizer, localized builder, visible-copy resolver) reads fenced objects.

## Blockers

None.

## Final Summary

Pending.
