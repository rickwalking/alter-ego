# AE-0071 — Context map and ubiquitous glossary

Status: Dev Complete
Tier: T2
Priority: High
Type: Docs
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: docs/ae-0071-context-map-glossary
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Accept (or revise) the nine proposed bounded contexts and publish one
glossary used by backend, frontend, tests, and docs.

## Problem

`CarouselProject` currently means at least eight different concepts, the
frontend has two hooks named `useBlogPosts()` with different semantics, and
terms like `status`, `publish`, and `source` are overloaded. The plan's
Phase 0 exit gate requires unambiguous definitions before any module work.

## Scope

- Run a focused context-mapping pass over the proposed contexts in
  `.agent/reports/domain-modularization.options.md` ("Proposed Contexts"),
  as amended by the 2026-06-12 interview: `persona` and `quality` are two
  contexts (persona owns VoiceScore/enforcement; quality consumes via
  persona's contract) and `editorial_operations` is a full module.
- **Transcribe (do not re-decide)** the Human Checkpoint answers from
  `.agent/reports/domain-modularization.interview.md`: EditorialProject;
  one BlogPost aggregate with `origin: carousel | standalone`
  (CarouselArticle rejected → glossary _Avoid_ list); persona/quality
  split; editorial_operations as module. Record each with its interview
  rationale.
- Publish `docs/architecture/domain-glossary.md` covering at minimum:
  `EditorialProject`, `EditorialWorkflow`, `CarouselPresentation`,
  `CarouselSlide`, `ArtifactBuild`, `BlogPost` (with `origin`),
  `VoiceScore`, `ChannelPublication`, `DistributionCopy`,
  `SourceMaterial`, `ResearchSource`, `MessageCitation`, and the four
  status families (`build_status`, `phase_status`, `review_status`,
  `publication_status`). Use the grill-with-docs format: one canonical
  term, rejected synonyms under _Avoid_ (`CarouselProject`,
  `CarouselArticle`, `persona_quality`, `ContentProject`, `Campaign`).
- Record the accepted context map (diagram or table) in the same document.

## Non-Goals

- No renames in code, database, or API (compatibility terms stay).
- No ADR text (AE-0072 consumes this output).

## Acceptance Criteria

- [ ] `docs/architecture/domain-glossary.md` exists and defines every term
      listed in Scope with a one-line definition and owning context
- [ ] WHEN a term has a legacy alias (e.g., `carousel project`) THE glossary
      SHALL mark it "compatibility term only" with its replacement
- [ ] All five Human Checkpoint questions have a recorded decision and
      rationale in the glossary or its appendix
- [ ] The accepted context map lists each of the nine contexts with its
      classification (core/supporting/generic/technical) and one-line charter
- [ ] `Carousel`, `EditorialProject`, `BlogPost`, `Publication`,
      `Workflow`, `Source`, and the status terms each map to exactly one
      definition (no term defined twice)
- [ ] `rg -c "useBlogPosts" frontend/src` output is cited in the glossary's
      naming-collision appendix as evidence for the `CarouselArticle` split
- [ ] The glossary states that Human Checkpoint question 6 (operating
      context) is decided in ADR-0009 (AE-0072), not here

## Gherkin Scenarios

Not applicable — documentation only; no runtime behavior changes.

## Delta

### ADDED

- `docs/architecture/domain-glossary.md`

### MODIFIED

- None

### REMOVED

- None

## Affected Areas

- Backend: none (reference only)
- Frontend: none (reference only)
- Database: none
- API: none
- Tests: none
- Docs: `docs/architecture/domain-glossary.md`
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: AE-0072
- Blocked by: none
- Related: AE-0070

## Implementation Plan

1. Extract the term tables from the research/options reports.
2. Decide the five checkpoint questions; record rationale.
3. Write the glossary and context map; cross-link both reports.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-12 00:00

Ticket created by planner.

## Files Touched

- docs/architecture/domain-glossary.md (new)

## Test Evidence

Docs-only ticket; no runtime tests. `rg -c "useBlogPosts" frontend/src` re-run and
the citation in the glossary naming-collision appendix matches live output (6 files).
Term-uniqueness self-check passed; all 7 ACs self-checked PASS (see dev-summary).

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
