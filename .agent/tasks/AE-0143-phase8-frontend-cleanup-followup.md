# AE-0143 — Phase 8 frontend cleanup follow-up (consent-gated)

Status: Intake
Tier: T2
Priority: Medium
Type: Task
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0143-phase8-frontend-cleanup
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Consent-gated follow-up capturing the items Phase 7 (AE-0134..0142) deliberately DEFERRED to keep the
frontend bounded-context alignment behavior-preserving. Belongs to roadmap Phase 8 ("Remove legacy layers and
adapters"). Not to be executed without explicit approval.

## Problem

Phase 7 reorganized `frontend/src/features/**` into `modules/<context>` behind public contracts and ratcheted
the cross-context boundary count to 0 — but, to stay byte-identical, it left compatibility shims and some
generic-vs-business component ambiguity in place, and did not relocate route-adjacent auth code.

## Scope (DEFERRED from Phase 7 — execute in Phase 8 with consent)

- **Remove the legacy `@/features/*` re-export shims** once no import (incl. tests) references them; delete the
  now-empty `src/features/` tree.
- **Exhaustive component re-homing:** move any remaining domain-named components still in
  `components/atoms|molecules|organisms` into their owning module (Phase 7 did the clear-cut ones:
  PersonaCard/RubricCard/BlogPostCard/KanbanBoard); keep generic `Neon*` primitives atomic.
- **Route-page thinning:** reduce `app/**/page.tsx` to thin composition over module hooks where it can be done
  without behavior risk (Phase 7 kept pages as-is).
- **Frontend `identity` module:** consolidate auth/session (currently in `lib/` + `app/`) into
  `modules/identity` behind a public contract (route-adjacent; needs care).
- **Flip the OpenAPI/Zod schema-drift check (AE-0141) to blocking** once the 24 advisory drift findings are
  reconciled to 0.
- Remove the `_example` boundary anchor once the checker has real modules to scan (it now does).

## Non-Goals

- No execution without explicit consent (this is the deferral record).
- No behavior change beyond the cleanups above.

## Acceptance Criteria

- [ ] Legacy `@/features/*` shims removed; `src/features/` deleted; no production import uses legacy paths
- [ ] Remaining domain components re-homed; generic Neon* primitives stay atomic
- [ ] Route pages are thin composition components
- [ ] `modules/identity` owns auth/session behind a public contract
- [ ] Schema-drift check flipped to blocking (drift = 0)
- [ ] All frontend gates green; boundary count held at 0

## Gherkin Scenarios

Not applicable — cleanup/refactor; verified by the green-gate safety net.

## Dependencies

- Blocks: —
- Blocked by: AE-0134 (Phase 7 epic merged)
- Related: AE-0142, AE-0141, AE-0133

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by AE-0142 exit gate as the consent-gated Phase 8 frontend-cleanup follow-up.

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
