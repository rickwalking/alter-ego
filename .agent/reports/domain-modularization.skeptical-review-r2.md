# Cold Critic Review (Round 2)

## Verdict: WARN

The amendments are directionally correct and the original three blockers have been accepted with credible closure criteria. However, the amendments introduce or fail to resolve **five material new concerns** — two of which are potential blockers that must be resolved before authorization to proceed. The plan has moved from "not credible" to "credible with significant caveats."

---

## Findings

### [BLOCKER] 1. Phase 2.5 scope is 2–4x the estimate and blocks everything else

- **Assumption:** Phase 2.5 can be completed in 1–2 weeks by a single contributor.
- **Risk:** The scope enumerated in the Phase 2.5 deliverables is enormous for one person: (a) complete a full field-level ownership map for a 12,405-line carousel service surface, (b) build a read-only compatibility adapter producing three logical snapshots from production rows, (c) capture and replay sanitized LangGraph checkpoints across new package boundaries, (d) implement `lock_version` enforcement from scratch (the column exists but no code touches it — this is new functionality, not refactoring), (e) exercise conflict behavior, (f) prove duplicate artifact-build/resume idempotency, (g) run authorization policy contract tests across three entry-point types (HTTP, agent-tool, worker), and (h) execute a full rollback drill with compatibility data, events, projections, *and* checkpoints. Each of (d), (f), (g), and (h) could be 2–5 days alone. And *all* of Phase 4–8 production write redirection is blocked until this passes plus a second cold review. If Phase 2.5 takes 4–6 weeks instead of 1–2, the entire 3–5 month plan is delayed by 25–50% before any behavior changes reach production.
- **Impact:** A credible risk that Phase 2.5 consumes 4–6 weeks, the single contributor loses momentum, the plan stalls, and the AE-0040 backlog diverges further. The plan has no circuit-breaker for Phase 2.5 overrun.
- **Suggested mitigation:** (1) Explicitly split Phase 2.5 into a mandatory core (field ownership map + `lock_version` enforcement + read-only adapter) and a stretch layer (rollback drill + full three-entry-point authorization tests). Make the stretch layer a Phase 2.5 bonus that can continue in parallel with Phase 3–4 *planning* but not with write redirection. (2) Add an explicit overrun threshold: if Phase 2.5 exceeds 3 weeks, require a checkpoint decision (continue vs. redirect scope) rather than silently absorbing the delay.
- **Open question for author:** What is the *minimum* set of Phase 2.5 deliverables you would accept as evidence before authorizing Phase 3–4? Can the rollback drill and the three-entry-point authorization tests be deferred to Phase 4 exit gates without reintroducing the original `BLOCK` concerns?

---

### [BLOCKER] 2. Circular dependency between Amendment 4 and Phase 2.5 exit criteria

- **Assumption:** The operating-context calibration (Amendment 4) and Phase 2.5 can proceed in parallel or sequentially without conflict.
- **Risk:** Amendment 4 says the scaled-down track replaces "per-slice parity/alerting requirements" with "trace-correlated smoke comparisons" and reduces rollback drills to "database backup + fresh-migration test + checkpoint fixture replay." But Phase 2.5's exit gate requires executing "a rollback drill with compatibility data, events, projections, and checkpoints" — which is specifically the *full* heavyweight version. The plan never states which track Phase 2.5 is operating under. If the operating context turns out to be pre-production/low-traffic, Phase 2.5 should shrink too. But if Phase 2.5 shrinks, it may not produce enough evidence to unblock Phase 3–4. Conversely, if Phase 2.5 runs full steam and then the operating-context statement picks the scaled-down track, Phase 2.5 was over-engineered.
- **Impact:** Phase 2.5 is either over-scoped for its context or under-scoped to produce the required evidence. The exit gate is ambiguous until the operating-context statement is drafted, but the operating-context statement (Phase 0) precedes Phase 2.5 — so this *can* be resolved, but only if Phase 0 explicitly decides the track *and* Phase 2.5's exit gate is rewritten to reference that decision.
- **Suggested mitigation:** Rewrite the Phase 2.5 exit gate to be parametric on the operating context: "If the full track applies [criteria], exit requires [full rollback drill + three-entry-point auth tests]. If the scaled-down track applies [criteria], exit requires [database restore drill + checkpoint fixture replay + trace-correlated smoke comparison]. The choice is recorded in ADR-0009 before Phase 2.5 begins."
- **Open question for author:** Which Phase 2.5 deliverables are absolute (field ownership map, read-only adapter, `lock_version` enforcement) regardless of track, and which are contingent on the operating-context decision?

---

### [WARN] 3. "No finding was waived" is technically true but masks significant deferral risk

- **Assumption:** Accepting a finding with a deferred closure criterion is equivalent to resolving it.
- **Risk:** Every Round 1 finding was "accepted," but the closure criteria for most are exit gates in Phases 2–6. For example: "Outbox delivery design and replay/dead-letter runbook are approved" — but the outbox isn't designed until Phase 6 (or Phase 0 at earliest). "Expected-version, idempotency, serialization, and freshness contracts pass tests" — these tests are written during their respective phases over a 3–5 month span. The plan has no mechanism to ensure that a finding accepted in principle doesn't get silently descoped when the phase arrives. The plan also adds a *new* set of requirements in the "Required Supporting Designs" section (outbox semantics, checkpoint compatibility, concurrency contract, operational equivalence, adversarial test matrix) without assigning them to a phase or estimating their effort. The adversarial test matrix alone is a multi-week effort per phase.
- **Impact:** The single contributor faces 3–5 months of concurrent modularization *and* test-infrastructure buildout *and* design-document authoring. The most likely outcome is that testing and design documents get shortened or deferred, and the very risks the review identified re-emerge in production.
- **Suggested mitigation:** (1) Assign each "Required Supporting Design" to a specific phase with a timebox. (2) Add a lightweight mechanism: before each phase gate, re-read the corresponding acceptance criterion from the decision log and confirm it's still on track. (3) Expose the cumulative testing/documentation effort in the estimate — right now it's hidden inside "12-20 engineer-weeks" with no explicit breakdown.
- **Open question for author:** Can you publish a rough effort breakdown (design + scaffolding vs. testing vs. behavior moves vs. cleanup) so the reviewer can judge whether the adversarial test matrix and supporting designs fit within the estimate?

---

### [WARN] 4. The Redis-outbox ambiguity hides a material design fork

- **Assumption:** Phase 0 either reorders the Redis publish or builds a minimal outbox, and either choice is acceptable.
- **Risk:** These are *fundamentally different* solutions with different correctness properties. Option A (reorder: persist → commit → publish) eliminates the crash-between-commit-and-publish gap but does not provide at-least-once delivery, does not deduplicate, does not have a replay mechanism, and does not de-risk Phase 6 at all. Option B (minimal outbox) provides durable delivery, deduplication, replay, and directly de-risks Phase 6 — but it is 3–10× the effort and changes the event infrastructure. If Phase 0 picks Option A (quick fix), then Phase 6 will need to build the outbox from scratch, and the "minimal outbox de-risks Phase 6" claim was wasted words. If Phase 0 picks Option B (minimal outbox), then Phase 0 is no longer "3-5 days" — it's potentially 2-3 weeks plus a new table and migration.
- **Impact:** The Phase 0 estimate is unreliable until this decision is made. The "minimal outbox" suggestion in the plan implicitly biases toward Option B, but the "fix the bug" framing biases toward Option A. The plan talks out of both sides of its mouth.
- **Suggested mitigation:** Explicitly decide in the plan: Phase 0 implements the reorder-only fix (cost: 1 day). The outbox is a Phase 6 design deliverable (already part of that phase's scope). The "minimal outbox in Phase 0" option is removed from the plan unless you formally re-scope Phase 0 to 2-3 weeks and re-baseline the estimate.
- **Open question for author:** Are you willing to commit to the reorder-only fix in Phase 0 and accept that Phase 6 will build the full outbox, or do you want the minimal outbox in Phase 0 (and accept the 2-3 week Phase 0)?

---

### [WARN] 5. No dependency injection strategy is specified

- **Assumption:** The composition root, module bootstrapping, and "no container/service-locator access from application code" rule can be implemented without choosing a DI mechanism.
- **Risk:** The choice of DI framework or pattern (manual wiring, `dependency-injector`, `fastapi-injector`, `lambdas/dataclasses`) directly affects every phase. It determines how module bootstraps receive their dependencies, how adapters are swapped in tests, how the request-scoped unit of work reaches handlers, and how the legacy compatibility layer wires in. If the wrong mechanism is chosen in Phase 1 scaffolding, it will need to be refactored across all modules in later phases — exactly the kind of churn the plan is supposed to reduce. "Manual wiring" is simplest but becomes unwieldy at 9 modules × multiple adapters each. A DI framework adds a dependency and learning curve.
- **Impact:** The Phase 1 scaffolding could lock in a wiring approach that proves insufficient by Phase 4, requiring either a mid-plan DI migration or a patchwork of workarounds.
- **Suggested mitigation:** In Phase 0 or Phase 1, evaluate and record the DI approach with a lightweight ADR. The choice matters less than having it be explicit and reversible. At minimum, state the default assumption (e.g., "manual wiring via `bootstrap_module(platform, session_factory)` until the module count exceeds 5, then evaluate `dependency-injector`").
- **Open question for author:** What is your current assumption for how module bootstraps receive their dependencies and how the request-scoped UoW is injected into handlers? Do you intend to evaluate a DI framework during Phase 1, or is there already a preferred pattern in the codebase?

---

### [INFO] 6. The frontend estimate confidence is near zero

- **Assumption:** Phase 7 (frontend alignment) is 1-2 weeks, partially parallel with Phases 4-6.
- **Risk:** The codebase verification found the frontend baseline "does not reproduce" — the research reported 41,638 lines; the actual is ~25,700 lines. The estimate for Phase 7 was based on the wrong number. The plan acknowledges this ("must be re-measured... before Phase 7 and the overall estimate are re-confirmed"), which means the current 12-20 engineer-week estimate includes a frontend number that is known to be unreliable. For a single contributor, a Phase 7 that takes 3-4 weeks instead of 1-2 weeks adds 1-2 months to the calendar.
- **Impact:** The total estimate is unreliable until the frontend baseline is re-measured. The 3-5 month calendar forecast should have a ±30% confidence interval.
- **Suggested mitigation:** Push the frontend re-measurement to Phase 0 (it's already scheduled there). But also add a note: until the re-measured baseline is published, the 12-20 week estimate is bracketed as "preliminary, ±25%."
- **Open question for author:** Once the frontend baseline is re-measured in Phase 0, will you re-publish the estimate with a confidence range?

---

## Missing evidence

- **DI framework evaluation.** The plan introduces a wiring-heavy architecture (composition root, 9 module bootstraps, request-scoped UoW, legacy compatibility layer) but does not specify the injection mechanism. A lightweight ADR comparing 2-3 options is needed before Phase 1 scaffolding locks in a pattern.
- **Phase 2.5 risk budget.** The plan has no explicit mechanism for detecting that Phase 2.5 is overrunning its 1-2 week estimate and no decision rule for what to do if it does (shrink scope? defer? cancel downstream phases?).
- **Testing effort breakdown.** The adversarial test matrix, Gherkin scenario writing, contract tests, rollback drills, and event replay tests are referenced but their effort is not estimated. This work could easily equal or exceed the behavior-migration effort per phase.
- **Checkpoint format inventory.** The plan says to "inventory persisted checkpoint backends and workflow versions" but does not report whether this inventory has even a preliminary result. If LangGraph checkpoints are opaque serialized blobs with no version field, the checkpoint-migration strategy changes materially.

---

## Residual risks if plan proceeds unchanged

1. **Phase 2.5 overrun cascades.** If Phase 2.5 takes 4+ weeks (plausible given scope), the entire plan's calendar blows by 25-50% before any behavioral changes reach production. The plan has no overrun detection or circuit-breaker.
2. **Track ambiguity stalls Phase 2.5.** If the operating-context statement hasn't been drafted by the time Phase 2.5 starts, the exit gate is ambiguous and the second cold review cannot judge whether the evidence is sufficient.
3. **Testing debt accumulates.** With all testing scope deferred to phase exit gates and no estimate for it, the single contributor will predictably cut testing under calendar pressure, re-introducing the very risks the cold review process was supposed to eliminate. The plan needs an explicit statement: "If testing scope threatens the calendar, the phase is delayed, not the testing descoped."
4. **Forked outbox approach wastes effort.** If Phase 0 implements the reorder-only fix and Phase 6 builds the outbox from scratch, the "minimal outbox in Phase 0 de-risks Phase 6" paragraph in the plan becomes misleading dead text. The plan should commit to one path.
5. **DI framework rework.** If Phase 1 scaffolds with ad-hoc wiring and Phase 4's module count makes it unmanageable, a mid-plan DI migration adds 1-2 weeks of non-value-adding churn.

---

**Bottom line for the author:** The plan has moved from "this won't work" to "this could work if you explicitly resolve these five open questions first." I recommend drafting responses to the five open questions above (particularly the Phase 2.5 scope/overrun question and the operating-context circular dependency), tightening the outbox commitment, and adding a DI decision before scheduling the third review. With those resolutions, the plan would reach `PROCEED_WITH_CAUTION`.

## Review provenance

- Reviewer: separate ephemeral OpenCode session (model kimi-k2.6, plan/read-only agent)
- Reviewer workspace: `/tmp/cold-critic-r2`
- Input: cold-critic system prompt plus plan-only blind packet (round-2 framing)
- Repository access: not provided
- Note: codex CLI (round-1 reviewer) hit a usage limit; OpenCode is the next reviewer in `skills/delivery/architect-skill/config.yaml`
- Date: 2026-06-12
