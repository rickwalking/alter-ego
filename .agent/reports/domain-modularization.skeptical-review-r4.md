# Cold Critic Review — Round 4 (Delta)

## Verdict

**PROCEED_WITH_CAUTION**

The interview decisions are generally consistent with a pre-production, single-user, no-external-consumers system and do not introduce anything *unsafe* at that operating level. However, the delta contains three material inconsistencies and one underspecified design point that, if unaddressed before Phase 1 starts, will result in rework, scope surprises, or a stalled partial migration.

---

## Findings

### [WARN] Phase 2.5 checkpoint replay mandate conflicts with finish-or-restart policy

- **Assumption:** The Phase 2.5 core deliverables — "capture and replay sanitized workflow checkpoints across old/new package boundaries" and "prove duplicate artifact-build and resume commands have one business effect" — provide forward value under the finish-or-restart policy.
- **Risk:** The interview settled on finish-or-restart: in-flight workflows are finished on old code or restarted with the owner's consent; no cross-version checkpoint migration tooling is built. Under that policy, a cross-package checkpoint replay test validates only that the test harness itself works. The old-to-new resume path will never execute in production. The pass/fail result has no operational consequence.
- **Impact:** 3–10 days of the Phase 2.5 core budget (at 5–10 h/week, that's 1–2 calendar weeks) is consumed on an exercise that proves nothing about the production path. This is scope the calendar cannot afford, and its inclusion undercuts the finish-or-restart decision's purpose.
- **Suggested mitigation:** Redefine the Phase 2.5 checkpoint deliverable: capture sanitized checkpoints *for inventory purposes only* (confirm serialization format, count live checkpoints, document state fields). Delete the "replay across old/new packages" requirement and the "prove duplicate command idempotency via replay" scope item. Instead, add a one-sentence Phase 4 or 5 exit-gate criterion: "any unsupported checkpoint identified in the Phase 2.5 inventory was either finished before migration or restarted with documented owner consent."
- **Open question for author:** What specific production behavior does the cross-package replay test protect, given that the owner will never rely on it? If the answer is "none, but it builds confidence in the compatibility adapter," that is a cost that should be weighed against the 1–2 calendar weeks it consumes from a constrained budget.

---

### [WARN] Finish-on-old-code and migrate-in-place have an unaddressed ordering constraint

- **Assumption:** "Finish in-flight workflows on old code" and "migrate schemas with data-preserving Alembic revisions" can happen independently.
- **Risk:** Migrate-in-place allows tables and columns to be renamed/reshaped during a phase. If a workflow's checkpoint references `carousel_projects.blog_markdown` and phase migration renames/removes that column, the old code (which must "finish" the workflow) cannot run against the migrated schema. The two operations — finish-on-old-code and schema-migrate — share a critical ordering: you must finish ALL workflows before the schema changes, or the finish path breaks.
- **Impact:** If a long-running workflow cannot be finished quickly (because it requires human review steps, AI generation, or external API calls), the owner must either (a) schedule schema migration after all workflows finish (indefinite delay), (b) restart the workflow (data loss for its intermediate state), or (c) keep the old column alive as a dead compatibility shim (contradicts migrate-in-place intent). The plan does not acknowledge this trilemma.
- **Suggested mitigation:** Two options, pick one before Phase 2.5: **(a)** Before any schema-modifying migration, the owner runs an explicit "drain checkpoint work" step: list every live checkpoint, either finish it (old code still works because schema hasn't changed) or restart it (with documented consent). Add this as a Phase 4 preamble. **(b)** If the owner accepts that some workflows will be restarted with state loss, record that explicitly in the checkpoint policy ("finish-or-restart, with restart preferred before schema changes") and add a one-line inventory step before each schema migration to confirm no workflow has unacceptable state.
- **Open question for author:** Do you accept that a long-running workflow during a migration phase may lose its intermediate state (restart), or do you need a no-data-loss property? The answer determines whether a "drain before migrate" step is advisory or mandatory.

---

### [WARN] Persona/Quality split and Editorial Operations full module are additive scope not reflected in the calendar

- **Assumption:** The calendar reforecast (5–10 h/week, 2–3× engineer-week estimate) is sufficient to cover the deviated decisions.
- **Risk:** Two interview decisions *increased* scope relative to the round-3 plan baseline:
  1. **Persona/Quality split** — Instead of one `persona_quality` module with one bootstrap, one `public.py`, one set of contract tests, one Import Linter rule, and an internal interface (which could be a private protocol), there are now two separate modules with a documented dependency direction (quality → persona), each needing a bootstrap, a public API, contract tests, boundary rules, and a compatibility test that the dependency doesn't reverse. This is ~40–60% more module-infrastructure code for this single domain concept.
  2. **Editorial Operations as a full module** — Instead of "read-side projections initially" (which Phase 6 would build as query views, ~2–3 days), the decision mandates "real behavior from day one: notification dispatch, board/calendar rules." Notification dispatch means event handlers, delivery adapters, retry/queue logic — genuine behavioral scope. Calendar rules mean scheduling logic, conflict resolution, deadline computation. The round-3 plan did not design for this; Phase 6's deliverable ("Build public blog, calendar, board, and analytics from read models") understates it by calling Calendar a "read model."

  These two deviations together add an estimated 1.5–3 engineer-weeks (~3–9 calendar weeks at 5–10 h/week) of unplanned scope. The plan's "migrate-in-place partially offsets this by deleting the compatibility-scaffolding work" accounting note does not mention these additions.
- **Impact:** The calendar will overrun the 6–12 month range unless either the deviations are reversed or the estimates are revised upward and the owner accepts the longer timeline. An undetected overrun erodes trust in the planning basis and risks project abandonment.
- **Suggested mitigation:** Before Phase 1, do one of: **(a)** Record the scope delta explicitly in ADR-0009: a line-item showing that persona/quality split and editorial_operations full module add +X engineer-weeks (+Y calendar weeks at 5–10 h/week). Publish the revised calendar total. **(b)** Revert to the round-3 recommendations for these two points (single persona_quality module; editorial_operations as read-projections initially), with a documented "split-later" or "promote-later" gate. **(c)** If the deviations are non-negotiable, explicitly descope something of equal weight from the plan (e.g., defer one module extraction to post-migration cleanup).
- **Open question for author:** Are persona/quality split and editorial_operations-as-full-module must-haves, or nice-to-haves? If must-haves, the calendar estimate needs a published upward revision. If nice-to-haves, revert to the lighter-weight approach and schedule a "promote later" ADR.

---

### [INFO] Per-migration-window "one writer" is underspecified for 5–10 h/week pacing

- **Assumption:** "Within any one migration window there is still exactly one writer" is a sufficient replacement for the long-lived sole-legacy-writer rule (round-1 BLOCKER).
- **Risk:** The plan does not define what a "migration window" is in calendar terms. If Phase 4 ("Introduce EditorialProject facade over CarouselProject") has a 1–2 engineer-week estimate, that is **3–6 calendar weeks at 5–10 h/week**. During those 3–6 weeks, editorial handlers (via the facade) and whatever still writes to `carousel_projects` (e.g., the legacy workflow route, workers that haven't been redirected yet) coexist. The "exactly one writer" rule must hold for the *entire duration* of the migration window, not just the instant of the migration commit. If the writer is the `legacy.carousel_project` coordinator, then editorial handlers are NOT writing directly to `carousel_projects` — they are calling the coordinator. But the interview's per-migration-window discipline language relaxes this: "no long-lived dual representations" and "per-migration-window discipline" could be read as allowing direct module writes during the window, which would violate the original single-writer BLOCKER.
- **Impact:** If the one-writer rule is inadvertently relaxed because "migration window" was not clearly defined, Phase 4 could have editorial and presentation both writing to the same rows for 3–6 calendar weeks without a single writer coordinator. This was the exact scenario the round-1 BLOCKER was designed to prevent.
- **Suggested mitigation:** Clarify in ADR-0009: "During a migration window, the legacy carousel row has exactly one writer — either a legacy coordinator or the single module performing the migration. Direct writes from multiple modules to the same table during any phase are prohibited, even within a migration window." Also record the longest expected migration window duration explicitly (suggested ceiling: 2 calendar weeks of wall-clock time, enforced by the phase exit gate).
- **Open question for author:** Does "per-migration-window discipline" mean editorial can write to `carousel_projects` directly during Phase 4's migration window (as long as presentation doesn't write simultaneously), or does a legacy coordinator remain the sole writer throughout? The answer determines whether the round-1 BLOCKER mitigation is preserved.

---

## Missing evidence

- **Live checkpoint inventory** (count, complexity, owner-estimated finish cost). The Phase 0 deliverable only specifies format detection (pickled vs JsonPlus) and absence of versioning. The number of in-flight workflows matters for the finish-or-restart decision: 0 checkpoints makes the concern academic; 50 checkpoints makes the ordering constraint in Finding 2 material.
- **Migration window duration ceiling.** The plan needs an explicit recorded bound (e.g., "no migration window exceeds 2 calendar weeks") so that the per-migration-writer discipline can be enforced.
- **Accounted scope delta for deviated decisions.** The calendar reforecast says "migrate-in-place partially offsets" but does not show the math. A line-item delta showing what was removed (compatibility scaffolding) vs what was added (persona/quality split cost, editorial_operations full-module cost) is needed to make the calendar credible.

---

## Residual risks if plan proceeds unchanged

1. **Phase 2.5 checkpoint replay consumes 1–2 calendar weeks of disposable effort**, narrowing the calendar margin before the first real phase exit gate (Phase 4). If Phase 0 itself overruns (its twelve deliverables were flagged as a risk in round 3), the checkpoint replay waste compounds the delay.
2. **An unaddressed ordering gap between finish-on-old-code and migrate-schema** could force the owner to restart workflows with undocumented state loss, or to keep dead schema columns alive for compatibility, undercutting the migrate-in-place benefit.
3. **The persona/quality split and editorial_operations scope additions, if not formally re-estimated, will silently inflate the 6–12 month calendar** — likely pushing it toward 10–16 months. A project with that duration on a nights/weekends schedule faces high abandonment risk. The plan has no mid-point abandonment check or milestone that asks "should we continue?"

---

## Review provenance

- Reviewer: separate ephemeral OpenCode session (model kimi-k2.6, plan/read-only agent)
- Reviewer workspace: `/tmp/cold-critic-r4`
- Input: cold-critic system prompt plus plan-only blind packet (round-4 DELTA framing: amended plan + interview record)
- Repository access: not provided
- Date: 2026-06-12
