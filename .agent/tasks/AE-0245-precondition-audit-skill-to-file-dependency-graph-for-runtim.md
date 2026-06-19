# AE-0245 — Precondition audit: skill-to-file dependency graph for runtime skills relocation

Status: Intake
Tier: T1
Priority: High
Type: Quality
Area: backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Before a single runtime skill file is moved, produce a complete skill→file dependency
graph (every `_shared/` cross-reference + every load path + the Dockerfile copy + the
CI skill-path gate) and confirm the repo-root symlinks are production-dead — so the
RES-8 relocation (AE-0246) cannot cause a prod `FileNotFoundError` on auto-deploy.

## Problem

The skeptical pass disproved the premise that `skills/runtime/` is "an empty
container": `find skills/runtime -type f` = **20 files** — 5 phase `SKILL.md` + 6
`_shared/*.md` standards + contracts/manifest, where the phase skills
**cross-reference the `_shared/*.md` standards by relative path**. So the runtime
skills are a **coupled tree**, not loose files: moving a phase skill without its
`_shared` siblings breaks the references. Because **merging to `main` auto-deploys
prod**, a wrong/incomplete move is a request-time `FileNotFoundError`.

The decision (decisions.md #2) is to **co-locate** these into their owning agent
package — a higher-touch move than "drop symlinks". The relocation (AE-0246) must
update **all six** consumers in lockstep, which requires the map this ticket produces
first.

Evidence: arch-plan §2.3 (precondition + the 6 load paths); skeptical-corrections.md
row 1 + revision #2; CLAUDE.md prod auto-deploy warning.

## Scope

Produce a deliverable dependency map (a report under `.agent/reports/` or
`docs/architecture/`) that audits ALL of:

1. `_shared/` cross-references **inside** the skill markdown — every relative
   link/`@include` between a phase `SKILL.md` and a `_shared/*.md`.
2. `application/services/carousel/phase_subagents.py` (loads phase-skill paths;
   ~`:27-62`).
3. `application/services/.../instruction_context_loader.py` (`:101` skill-context load).
4. `domain/constants/runtime_skills.py` (path constants +
   `get_runtime_skills_filesystem_root()`).
5. The **Dockerfile** copy path(s) into `/app/skills/runtime` (the prod resolution root).
6. The **CI skill-path gate** (`scripts/validate_skill_boundary.py` + any skill-path
   check).

Plus: confirm whether the repo-root symlinks (`skills/carousel-pipeline`, etc.) are
consumed by **any** prod path (expected: NO — prod resolves via
`get_runtime_skills_filesystem_root()`).

## Non-Goals

- **Move nothing.** This ticket is an audit/deliverable only; the actual relocation is
  AE-0246 (RES-8). Producing the map here keeps the high-risk move gated on evidence.
- Do not change loaders, Dockerfile, or the CI gate (AE-0246 does that in lockstep).
- Do not decide the `/carousel-pipeline` slash-command question's outcome — only
  record it as a finding for AE-0246.

## Acceptance Criteria

- [ ] A dependency-map deliverable exists listing, for each of the 5 phase skills and 6
      `_shared` standards: its file path, every relative reference to/from it, and which
      of the 6 consumers (above) resolves it.
- [ ] The map enumerates the **exact** path constants in
      `domain/constants/runtime_skills.py`, the Dockerfile copy line(s), and the CI
      skill-path gate assertions that the relocation must update.
- [ ] A documented finding states whether the repo-root symlinks are consumed by any
      prod path (with the grep/code evidence), i.e. confirms they are prod-dead (or
      flags any consumer found).
- [ ] A documented finding records whether any human/slash-command entrypoint
      references the runtime skills (the `/carousel-pipeline` open question), so AE-0246
      can decide on a shim.
- [ ] The map is explicitly referenced by AE-0246 as its precondition input.

## Gherkin Scenarios

> Audit/precondition ticket producing a deliverable map; no production code changes →
> **no `.feature` required** (AE-0153). The acceptance proof is the completeness of the
> map (all six consumers + cross-refs enumerated), validated by review.

```gherkin
Feature: Runtime-skill relocation is gated on a complete dependency map

  Scenario: The map enumerates every consumer of the runtime skills
    Given the 20 files under skills/runtime and their _shared cross-references
    When the dependency audit completes
    Then the map lists all six load paths that resolve those skills
    And it states whether the repo-root symlinks are consumed by any prod path
```

## Delta

### ADDED
- A skill→file dependency-map deliverable (report) under `.agent/reports/` or
  `docs/architecture/`.

### MODIFIED
- None (audit only).

### REMOVED
- None.

## Affected Areas

- Backend: read-only audit of `phase_subagents.py`, `instruction_context_loader.py`,
  `domain/constants/runtime_skills.py`.
- Frontend: none.
- Database: none.
- API: none.
- Tests: none (deliverable is a map, not code).
- Docs: the dependency-map report.
- Deployment: read-only audit of the Dockerfile skill-copy path + CI skill-path gate.

## Dependencies

- Provisional epic id: **RES-7** (Phase 2 — skills relocation precondition).
- Gating ADR: **ADR-0016** (per-agent façade packages + skill/tool contract) and the
  skills-layout intent in arch-plan §10 — the map informs where skills co-locate. No
  ADR must be Accepted to run the audit.
- Blocks: **AE-0246 (RES-8)** — the relocation MUST consume this map; do not move files
  without it.
- Blocked by: none.
- Related: AE-0223 (board/gitignore), the CI `validate_skill_boundary.py` gate.

## Implementation Plan

1. Enumerate the 20 files under `skills/runtime/`; extract every relative cross-ref
   between phase `SKILL.md` and `_shared/*.md`.
2. Trace each of the 6 consumers and record the exact path constants / copy lines /
   gate assertions they use.
3. Grep for any prod or slash-command consumer of the repo-root symlinks; record the
   finding (prod-dead or not).
4. Write the deliverable map; reference it from AE-0246.

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **Audit/precondition ticket — no production code change.** The output is a
  dependency map, not behavior. **No `.feature` required**; no static-analysis rule is
  added, so no AE-0180 seeded test applies.
- **No public/user-visible behavior change** — nothing ships to runtime.
- **Affected gates:** none changed here (the audit feeds AE-0246, which updates the CI
  skill-path gate in lockstep).
- Reviewer/QA to sign off on the no-`.feature` classification and the map's completeness.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated (all six consumers enumerated)
- [ ] Edge cases tested (every `_shared` cross-ref captured; symlink finding documented)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:30

Created from the agent-architecture-restructure epic (RES-7). This is the BLOCKER
precondition that makes the RES-8 co-location safe against a prod FileNotFoundError.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **Audit-before-move is mandatory.** The skeptical pass corrected the "empty
  container" premise: the runtime skills are a coupled tree with `_shared` cross-refs
  resolved by six consumers, and prod auto-deploys — so a blind move is a production
  outage class. This ticket produces the evidence that gates the move.
- **Deliverable is a map, not code** — keeping it a pure audit isolates the risk and
  gives AE-0246 a concrete checklist to update in lockstep.

## Blockers

None.

## Final Summary

Pending.
