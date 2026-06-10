# AE-0029 — Skill Boundary and Delivery Slash Commands

Status: Review
Tier: T2
Priority: Critical
Type: Feature
Area: Skills/DevOps
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: feat/ae-0029-skill-boundary
Kanban Card: TBD
Created: 2026-06-09
Updated: 2026-06-09

## Goal

Separate production runtime skills from developer delivery skills and prove every delivery slash command still resolves to the canonical skill.

## Problem

Runtime carousel instructions and delivery workflow skills currently share top-level `skills/*` paths. This risks packaging developer-only instructions into production images and makes active carousel instruction loading ambiguous.

## Scope

- Move canonical runtime behavior skills under `skills/runtime/`.
- Move canonical delivery workflow skills under `skills/delivery/`.
- Preserve temporary top-level compatibility links for local agent clients.
- Add deterministic skill-boundary validation.
- Build the backend image and assert it contains runtime skills only.
- Run and document the complete delivery slash-command smoke matrix.

## Non-Goals

- Changing carousel generation behavior.
- Implementing `hero_lower_third_v1` policy values.
- Removing compatibility links in this ticket.

## Acceptance Criteria

- [ ] WHEN delivery skills are validated THE tasklist SHALL prove every documented slash command and architect mode loads canonically, every frontmatter name matches, implicit activation is disabled, and plain-language controls remain inactive.
- [ ] WHEN the backend image is built THE IMAGE SHALL contain `/app/skills/runtime` and SHALL NOT contain `/app/skills/delivery`.
- [ ] WHEN the skill-boundary validator runs THE COMMAND SHALL reject runtime manifests that reference delivery paths.
- [ ] WHEN compatibility links are present THE VALIDATOR SHALL prove they resolve to canonical delivery or runtime folders and are not broken or circular.
- [ ] WHEN plain-language control prompts mention delivery activities THE SUPPORTED CLIENT SHALL NOT implicitly activate delivery skills.

## Gherkin Scenarios

```gherkin
Feature: Delivery skills remain slash-only after folder migration

  Scenario: Delivery slash commands resolve canonically
    Given canonical delivery skills are under skills/delivery
    When each documented slash command is invoked in a disposable fixture
    Then the expected canonical skill and mode load
    And client name, client version, command, exit status, and evidence are recorded

  Scenario: Production image excludes delivery skills
    Given the backend image is built
    When container-content validation runs
    Then /app/skills/runtime exists
    And /app/skills/delivery does not exist
```

## Delta

### ADDED

- `skills/runtime/` canonical runtime tree.
- `skills/delivery/` canonical delivery tree.
- Skill-boundary validator and tests.
- Slash-command smoke evidence artifact.

### MODIFIED

- `CLAUDE.md`
- `scripts/architect/run_cold_critic.sh`
- `.agent` workflow documentation.
- `phase_subagents.py`
- Carousel consolidation feature tests.
- ADR-007 path examples.
- BMAD manifest paths.
- Runtime skill references.
- Backend Docker skill copy source.

### REMOVED

- Production image inclusion of delivery skills.

## Affected Areas

- Backend: yes
- Frontend: no
- Database: no
- API: no
- Tests: yes
- Docs: yes
- Prompts/LLM: yes
- Observability: no
- Deployment: yes

## Dependencies

- Blocks: AE-0030, AE-0031, AE-0032, AE-0033, AE-0034, AE-0035, AE-0036, AE-0037, AE-0038, AE-0039
- Blocked by: AE-0028
- Related: `.agent/reports/AE-0028.arch-plan.md`

## Implementation Plan

1. Create canonical `skills/runtime` and `skills/delivery` trees.
2. Add temporary compatibility links for supported clients.
3. Update references, manifests, scripts, and docs to canonical paths.
4. Add deterministic validator for frontmatter, path boundaries, links, and required commands.
5. Update Docker packaging to copy only runtime skills.
6. Run slash-command smoke tests in disposable fixtures and record evidence.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-09

Ticket created from AE-0028 architecture plan.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Compatibility links are temporary discovery aids, not canonical storage.
- Docker must copy only `skills/runtime/`.

## Blockers

None.

## Final Summary

Pending.
