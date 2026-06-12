# Cold Critic Review (Round 3)

**Reviewer:** OpenCode / kimi-k2.6
**Review of:** `domain-modularization.options.md` (amended, 2026-06-11)
**Precondition:** Plan-mode; read-only; no repository or runtime access

---

## Verdict

**PROCEED_WITH_CAUTION** — Both round-2 BLOCKERs are resolved by credible amendments with clear linear sequencing. The plan is internally consistent on its own terms. However, three new material concerns (below) would escalate to BLOCKER if the Phase 0 operating-context statement or checkpoint inventory produces data that contradicts the plan's assumptions. The caution flag is on the Phase 2.5 core deliverable set, which exhibits known-optimistic sizing and a subtle contradiction that requires explicit resolution before approval of Phase 2.5 start.

---

## Findings

### [BLOCKER] None found

Both round-2 BLOCKERs have been resolved:

- **Phase 2.5 scope/overrun** → core/contingent split with a 3-week circuit-breaker and a documented overrun decision rule. The parametric structure is sound. The original circular dependency is broken into a linear dependency (Phase 0 → track choice → Phase 2.5 parametric gate).

- **Circular dependency (track vs exit gate)** → The track is recorded in ADR-0009 during Phase 0 as a Phase 2.5 precondition. Phase 2.5 cannot start with an ambiguous exit gate. Scaled-down deferrals are named to Phase 4's exit gate with explicit requirement that they complete before any carousel write redirection. The dependency chain is now: Phase 0 → track established → Phase 2.5 proceeds → scaled-down items caught at Phase 4 gate.

No round-2 finding was waived; all have documented closure criteria and phase assignments.

---

### [WARN] lock_version enforcement in Phase 2.5 creates an unacknowledged tension with the "no production write redirection" constraint

**Assumption:** "Introduce no production write redirection" in Phase 2.5 means no behavioral change to existing write paths during the risk spike.

**Risk:** Implementing expected-version enforcement on a column that has existed since migration 0002 but is checked by zero application code necessarily changes write semantics. Once enforced, any write path that omits `lock_version` (or provides a stale value) will return a 409 or raise an ORM `StaleDataError` — something that cannot happen today. This is a behavioral change to the *existing* write path, not a redirection to a *new* path, but it is a production-visible semantic change regardless of how you label it.

**Impact:** If the enforcement is rolled out to production during Phase 2.5, it can break in-flight workflows that never carried a version. If it is only enforced in CI/test (the only safe interpretation given the "no production write redirection" rule), then the "exercise conflict behavior against it" deliverable only proves the mechanism works in isolation — it does not prove it will work in production without regression.

**Suggested mitigation:** The plan should explicitly state the rollout strategy for `lock_version` enforcement (test-only? feature-flagged? production-enabled with a migration to backfill `lock_version` values?). If it remains test-only in Phase 2.5, the Phase 2.5 exit gate should record whether any live production rows have non-null `lock_version` values (and, if not, what the activation migration will do). Without this, the Phase 4 "first write redirection" will be the first time lock_version hits production — by surprise.

**Open question for author:** Can you confirm that `lock_version` enforcement in Phase 2.5 is **test/CI-only** and will not be deployed to production during Phase 2.5? If yes, add a sentence stating that. If no, explain how the "no production write redirection" rule and the enforcement coexist.

---

### [WARN] Phase 2.5 core layer is 5 substantial deliverables in 1-2 weeks — optimistic even for a single expert contributor

**Assumption:** The core layer (field ownership map, compatibility adapter, checkpoint replay, lock_version enforcement + conflict tests, duplicate-command tests) fits in 1-2 weeks.

**Risk:** A single contributor cannot deliver five items of this nature — each requiring code, tests, and in most cases data analysis — in 5-10 working days. The field ownership map alone requires auditing every column in `carousel_projects`, tracing every write site, and documenting invariants and command owners. The compatibility adapter requires implementing a read transformation that produces correct snapshots from real rows. Checkpoint replay requires understanding the serialization format, capturing fixtures, and demonstrating old-code resume.

**Impact:** If the core layer overruns even moderately (3-4 weeks), the 3-week circuit-breaker fires, resulting in a planning checkpoint that consumes additional time. The plan's calendar estimate of 3-5 months does not account for this scenario because the circuit-breaker pauses but does not specify a recovery trajectory — if the answer is "continue," there is no built-in compression of later phases.

**Suggested mitigation:** One of two approaches:
  1. State explicitly that the 1-2 week estimate for core is aspirational and that 3 weeks is the committed ceiling (the circuit-breaker does this implicitly, but the pre-circuit-breaker estimate should be honest).
  2. Reduce core scope to 3-4 deliverables and defer one (e.g., duplicate-command proofs) to Phase 4's adversarial test matrix, where they are more naturally exercised against real write redirection anyway.

**Open question for author:** What is the single most time-consuming item in the Phase 2.5 core, and does the 1-2 week estimate survive if that item takes 5 days alone?

---

### [WARN] No SSE event name migration strategy is documented

**Assumption:** "Existing response schemas remain stable" covers all transport contracts, including SSE event names.

**Risk:** The plan lists SSE event names under "Special handling required" in the anti-corruption layer section, but no phase deliverable explicitly addresses them. If the modularization changes internal event-type strings or the source handler's route registration (e.g., the SSE endpoint moves from a global route to a module's inbound adapter), event names or payload shapes can change. The frontend, which subscribes to named events, has no compile-time check and would silently stop receiving events or fail to parse them.

**Impact:** A client-side SSE subscription mismatch is a silent failure with no error dashboard unless explicit telemetry monitors event-type distribution. This could go undetected for hours or days in a single-contributor project without extensive monitoring.

**Suggested mitigation:** Add a Phase 4 or Phase 5 deliverable requiring an explicit inventory of SSE event type names and payloads, with a contract test ensuring event names survive migration. Alternatively, document in Phase 0 that SSE event names must be strictly preserved (as strings) across all migration phases, and add a CI ratchet that fails if an event name changes in the OpenAPI spec or route handler.

**Open question for author:** Are SSE event types versioned or string-constant? Is there a single source of truth for event names that the frontend and backend both reference?

---

### [WARN] Phase 2.5 overrun circuit-breaker has no defined recovery options

**Assumption:** "Work pauses for an explicit checkpoint decision — continue, re-scope, or re-sequence — recorded in the decision log" is a sufficient contingency.

**Risk:** When a single contributor is 3 weeks into Phase 2.5 and hits the circuit-breaker, the available options are:
- *Continue* — but there is no recovery plan; the overall estimate has already slipped with no compression mechanism.
- *Re-scope* — means dropping a core deliverable, which contradicts the lock_version enforcement and checkpoint replay mandates.
- *Re-sequence* — means moving work to a later phase, which risks the same silent-deferral problem the round-2 review flagged.

The circuit-breaker triggers a good conversation but has no decision framework. Under schedule pressure, a single contributor may default to "continue" and absorb the slippage into the overall timeline without a formal re-estimate.

**Impact:** The 3-5 month calendar estimate has no explicit buffer or contingency factored in. If Phase 2.5 takes 5 weeks instead of 2, the total estimate could grow 15-20% without any phase being "late" individually — just all sequentially sliding.

**Suggested mitigation:** Add two sentences to the circuit-breaker rule: (1) "If the decision is 'continue,' the total estimate is revised by the delta from the original plan and published." (2) "If the decision is 're-scope,' the dropped deliverable is explicitly named in the Phase 4 gate criteria so it is not lost." This mirrors what the plan already does for the scaled-down track's deferred items.

**Open question for author:** Under what conditions would you choose "re-scope" over "continue" for a Phase 2.5 core item, given that all core items are described as mandatory?

---

## Missing Evidence

1. **Actual Phase 0 duration bound.** The plan says Phase 0 is 1-2 weeks with 12 deliverables. No breakdown of how those 12 items stack into the timebox is provided. A deliverable-level time budget would let the reviewer independently assess whether Phase 0 is likely to complete on schedule (which matters because Phase 2.5 cannot start until Phase 0's track choice is recorded).

2. **Checkpoint serialization format.** The plan notes the checkpointer backends (postgres, sqlite, memory, disabled) and the absence of a version field, but does not state whether ser/des is Python pickle (class-path-dependent) or a portable format (JSON/dict). If pickle, **every module package rename breaks all existing SQLite checkpoints**, and Phase 2.5's checkpoint replay cannot succeed without a migration strategy. This is the single highest-materiality missing evidence item.

3. **SSE event type constants.** Are event names string literals in route handlers? Shared constants? Part of a schema? Without this, the migration risk for SSE is unquantifiable.

4. **lock_version production values.** A quick `SELECT lock_version, COUNT(*) FROM carousel_projects GROUP BY lock_version` would immediately tell whether the column has meaningful data (non-null, varied) or is entirely NULL. If the latter, enforcement will require a backfill migration and changes every write path, not just a decorator.

---

## Residual Risks If Plan Proceeds Unchanged

1. **Phase 2.5 overruns even with the circuit-breaker.** The core estimate is optimistic; the circuit-breaker provides a decision point but no recovery playbook. The 3-5 month calendar should be understood as "5-7 months if Phase 2.5 takes 4 weeks."

2. **lock_version enforcement surprises at Phase 4.** If enforcement is test-only in Phase 2.5 but hits production during Phase 4's carousel write redirection, the first real-world conflict behavior will be discovered at the most critical moment. The plan should front-load one production-like conflict test during Phase 2.5 (possibly as a conditional contingent item on whichever track is chosen).

3. **SSE event drift is the silent integration failure that components don't catch.** The plan has excellent compile-time/CI enforcement for imports, database schemas, and OpenAPI. SSE is the gap. A single sandbox diff comparison of event-type names before/after each phase would close it with near-zero effort, but no phase assigns it.

4. **Phase 0 scope has a 12-item backlog that may not fit 1-2 weeks.** If Phase 0 spills to 3 weeks, everything slides, and the Phase 2.5-start precondition is re-evaluated while the clock is already running against the plan's calendar.

---

**Bottom line:** The plan is materially better than the round-2 version. Both BLOCKERs are credibly resolved. The three new WARNs above are real but addressable through clarifications, not structural rework. If the Phase 0 checkpoint inventory reveals that checkpoints are Python-pickled with class paths, I would re-read that finding as a potential BLOCKER on Phase 2.5 start without a serialization migration plan. Same caveat applies if the `lock_version` column is entirely NULL in production and the enforcement strategy is not clarified before Phase 2.5 begins.

---

## Review provenance

- Reviewer: separate ephemeral OpenCode session (model kimi-k2.6, plan/read-only agent)
- Reviewer workspace: `/tmp/cold-critic-r3`
- Input: cold-critic system prompt plus plan-only blind packet (round-3 framing)
- Repository access: not provided
- Date: 2026-06-12
