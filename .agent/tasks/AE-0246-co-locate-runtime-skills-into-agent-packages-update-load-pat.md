# AE-0246 — Co-locate runtime skills into agent packages; update load paths, Dockerfile and CI gate

Status: Intake
Tier: T2
Priority: High
Type: Refactor
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Co-locate the runtime skills into their owning agent packages
(`carousel_agent/skills/…`, `alter_ego_agent/skills/knowledge-base/…`), update every
load path + the Dockerfile + the CI skill-path gate in lockstep, drop the dead
repo-root symlinks and the now-empty `skills/runtime/` — verified by a Docker image
build that resolves every skill path and a green CI skill-path gate.

## Problem

Runtime skills live under `skills/runtime/` (a 20-file coupled tree with `_shared/`
cross-references) and are intermixed at repo root with delivery skills via symlinks.
Per decisions.md #2 they should be **co-located with their owning agent package** so
the per-agent mental model holds and root `skills/` becomes delivery-only. Because
**merging to `main` auto-deploys prod**, a wrong/incomplete move is a request-time
`FileNotFoundError` (the highest-risk physical change in the epic) — the relocation
must update all consumers atomically and be verified inside the built image, not just
on a passing local tree.

Evidence: arch-plan §2.2 Option B + §2.3 (6 load paths) + §9 P2 row;
skeptical-corrections.md revision #2; ADR-0016 (façade + skill/tool contract);
CLAUDE.md prod auto-deploy warning.

## Scope

- Move runtime skills into agent packages: `carousel_agent/skills/…`,
  `alter_ego_agent/skills/knowledge-base/…`, preserving the `_shared/` cross-reference
  tree.
- Update **all six** consumers in lockstep (per the AE-0245 map):
  `domain/constants/runtime_skills.py` (path constants +
  `get_runtime_skills_filesystem_root()`), `phase_subagents.py`,
  `instruction_context_loader.py`, the Dockerfile copy path (`/app/skills/runtime` →
  new package paths), the CI skill-path gate (`scripts/validate_skill_boundary.py`),
  and any phase-skill path resolution.
- Drop the dead repo-root symlinks and the now-empty `skills/runtime/` container.

## Non-Goals

- Do not start the move without the **AE-0245** dependency map (precondition).
- Do not move `application/tools/` or services into the agent packages — only skill
  **content** (markdown) co-locates; tool adapters/business logic stay per the ADR-0016
  skill/tool contract (that contract's enforcement is AE-0250, RES-11).
- Do not change skill wording/standards — relocation only.
- Do not remove a delivery-skill symlink that backs a `/slash-command` (only the
  runtime-skill root symlinks are dead — confirm via the AE-0245 finding).

## Acceptance Criteria

- [ ] Runtime skills are physically under their agent packages with the `_shared/`
      cross-reference tree intact (every relative reference still resolves).
- [ ] All six consumers are updated in lockstep and reference the new paths; no consumer
      still points at `skills/runtime/`.
- [ ] The **Docker image builds** and **every skill path resolves inside the built
      image** (not just locally) — a path-resolution check runs against the image.
- [ ] The **CI skill-path gate** (`validate_skill_boundary.py`) is updated and runs
      **green**; all 5 carousel phase skills + the knowledge-base skill resolve at
      runtime.
- [ ] The dead repo-root symlinks and the empty `skills/runtime/` are removed; root
      `skills/` is delivery-only.
- [ ] Backend `pytest`/`mypy`/`ruff` green; the skill-path gate green.

## Gherkin Scenarios

> Behavior-changing at the deployment/path-resolution boundary (a wrong move breaks
> prod), so a `.feature` IS required — happy + edge + failure of skill resolution.

```gherkin
Feature: Runtime skills resolve from their co-located agent packages

  Scenario: Every carousel phase skill resolves after relocation
    Given the runtime skills are co-located under carousel_agent/skills
    When phase_subagents builds the phase subagent specs
    Then every phase SKILL.md and its _shared standards resolve to an existing file

  Scenario: Skill resolution works inside the built Docker image
    Given the Docker image is built with the new skill copy paths
    When get_runtime_skills_filesystem_root() resolves each skill path in the image
    Then every path exists and no FileNotFoundError is raised

  Scenario: A missing _shared standard is caught by the CI gate
    Given a phase skill references a _shared standard that was not co-located
    When the CI skill-path gate runs
    Then it fails (exit non-zero) and names the unresolved reference
```

## Delta

### ADDED

- Co-located skill trees under `carousel_agent/skills/…` and
  `alter_ego_agent/skills/knowledge-base/…`.
- A path-resolution check against the built image (and/or an extended CI gate).

### MODIFIED

- `domain/constants/runtime_skills.py`, `phase_subagents.py`,
  `instruction_context_loader.py`, Dockerfile, `scripts/validate_skill_boundary.py`.

### REMOVED

- Repo-root runtime-skill symlinks; the empty `skills/runtime/` container.

## Affected Areas

- Backend: skill loaders + path constants.
- Frontend: none.
- Database: none.
- API: none.
- Tests: skill-path resolution test/gate (+ a `.feature` for resolution behavior).
- Docs: update any doc that references `skills/runtime/` paths.
- Prompts/LLM: skill content relocates (no wording change).
- Observability: none.
- Deployment: **Dockerfile copy path changes** + CI skill-path gate — the riskiest
  surface; prod auto-deploys.

## Dependencies

- Provisional epic id: **RES-8** (Phase 2).
- Gating ADR: **ADR-0016** (per-agent façade + skill/tool contract; defines where
  skills co-locate) and arch-plan §2.3.
- Blocked by: **AE-0245 (RES-7)** — the dependency map is the mandatory precondition.
- Blocks: **AE-0250 (RES-11)** benefits from the co-located layout being in place.
- Related: AE-0223 (board), `validate_skill_boundary.py` gate.

## Implementation Plan

1. Consume the AE-0245 map; move the skill tree (phase skills + `_shared`) into the
   agent packages, preserving relative references.
2. Update all six consumers in lockstep; point
   `get_runtime_skills_filesystem_root()`/path constants at the new locations.
3. Update the Dockerfile copy path and the CI skill-path gate.
4. Build the image; assert every skill path resolves inside it.
5. Drop the dead root symlinks + empty `skills/runtime/`; run the gate + backend gates.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (missing `_shared` ref caught; image-path resolution; symlink removal)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:30

Created from the agent-architecture-restructure epic (RES-8). Highest-risk physical
change; gated on the AE-0245 dependency map and verified inside the built image.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **Lockstep update of all six consumers + in-image verification is mandatory.** Prod
  auto-deploys; a wrong path = request-time `FileNotFoundError`. Passing a local tree
  is insufficient — the build-the-image path-resolution check is the real guard
  (arch-plan §2.3).
- **Only skill content co-locates** — tool adapters/business logic stay per the
  ADR-0016 contract (enforced by AE-0250). This ticket does not move infra.
- **Root symlink removal is gated on the AE-0245 slash-command finding** so we don't
  break a human `/carousel-pipeline` workflow.

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **Behavior-changing at the deployment/path-resolution boundary** — a wrong move
  changes (breaks) runtime behavior. **`.feature` REQUIRED** (happy: skills resolve;
  edge: in-image resolution; failure: missing `_shared` caught by the gate).
- Not a pure refactor: the load paths + Dockerfile + CI gate change observable
  resolution behavior, so the AE-0153 refactor exemption does NOT apply.
- **Affected gates:** `validate_skill_boundary.py` skill-path gate + backend gates.

## Blockers

None.

## Final Summary

Pending.
