# AE-0057 — Add null safety for property access in `artifact_manifest.py`

Status: Intake
Tier: T2
Priority: Medium
Type: Refactor
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-11
Updated: 2026-06-11

## Goal

Fix PR #11 comment #10: "is it safe to access all these properties without checking? let's think about a better architect solution" in `backend/src/rag_backend/application/services/carousel/artifact_manifest.py` (line 171).

## Problem

Properties are accessed on objects without null/type checks. If the object is None or missing fields, this will raise AttributeError at runtime.

## Scope

- Review property access patterns in `artifact_manifest.py`
- Add null/type guards where properties might be None
- Use `getattr()` with defaults or explicit checks
- Consider a TypedDict or dataclass for the manifest structure

## Non-Goals

- Do not change the manifest generation output format

## Modularization Alignment (2026-06-12)

**SUPERSEDED — scope absorbed by AE-0042** (2026-06-12 scan). AE-0042's
conversion of `CarouselArtifactManifestPayload` to a Pydantic BaseModel
with typed access covers PR #11 comment #10 (unsafe access at
`artifact_manifest.py:171`) entirely. Remaining action here:

1. After AE-0042 merges, verify comment #10's line is covered by typed
   access and a test.
2. Close this ticket as duplicate-of AE-0042 with the verification
   evidence.

Do not implement independently — parallel edits to `artifact_manifest.py`
would conflict with AE-0042 and AE-0043 (which also touches the file).

## Acceptance Criteria

- [ ] All dynamic property accesses have null/type guards
- [ ] No bare `.attribute` access on unvalidated objects
- [ ] ruff check, mypy, pytest pass

## Affected Areas

- Backend: `application/services/carousel/artifact_manifest.py`

## Dependencies

- Blocks: None
- Blocked by: AE-0042 (absorbs this scope; this ticket is verification-only)
- Related: AE-0042 (null-safety theme)

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked
