# AE-0233 — Delete/archive superseded docs with inbound-link checks

Status: Intake
Tier: T2
Priority: Medium
Type: Quality
Area: Docs
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18
Source: architect plan — `.agent/reports/frontend-migrations-and-docs.arch-plan.md` (Thread B2). Parent: AE-0231.

## Goal
Remove deprecated docs without breaking links: archive large historical records,
hard-delete only no-inbound-link stubs.

## Problem
~11 superseded items (scan): PROFESSIONAL_PIVOT_PLAN, plan-sse-migration-v2,
cloudflare-ws-debug, backend/BACKEND_IMPLEMENTATION_PLAN, backend/AGENTIC_REFACTOR_PLAN,
superseded carousel/ae-0040 plans, rollback/ + assessment/. Several are linked from
README/CLAUDE.md, so blind deletion breaks links.

## Scope
- Create `docs/archive/`; `git mv` large historical records there.
- Hard-delete only stubs with zero inbound links (e.g. deployment/docker-compose.commands.md, public-chat-and-create-workflow-fixes.md).
- For each removal: grep inbound links (README, CLAUDE.md, other docs/ADRs) and fix/redirect them.

## Non-Goals
- Do not delete active plans (frontend-legacy-removal, agentic-delivery-system, etc.).

## Acceptance Criteria
- [ ] Superseded docs archived or deleted per the inbound-link rule.
- [ ] grep shows no broken `docs/...` links in README/CLAUDE.md/docs after the change.
- [ ] A short note in archive/INDEX.md explains what was archived and why.

## Dependencies
- Parent: AE-0231. Do before AE-0234 (so indexes reflect final layout).

## Progress Log
### 2026-06-18
Created from the architect plan (Thread B2).

## Files Touched
Pending.
## Test Evidence
Pending.
## QA Report
Pending.
## Blockers
None.
