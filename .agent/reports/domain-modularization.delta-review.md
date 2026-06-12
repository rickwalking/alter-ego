<!-- Provenance: external cold critic (OpenCode/CrofAI-kimi-k2.6), read-only, no conversation
context. Delta review of the migrate-in-place amendment vs the round-3 skeptical review.
Date 2026-06-12. Verdict: PROCEED_WITH_CAUTION (Phase 1 safe; F1-F4 are pre-Phase-4 items). -->

# Cold-Critic DELTA Skeptical Review — Analysis Complete

Below is my analysis of what the migrate-in-place amendment changed relative to the round-3 (codex) BLOCK verdict, and what it means for starting Phase 1.

## Delta Summary

The amendment (interview 2026-06-12 + ADR-0009) replaced four permanent risk‑machinery constructs with **time‑boxed, pre‑production‑scaled equivalents**:

| Round‑3 construct | Amendment replacement |
|---|---|
| Permanent legacy ACL | Per‑migration‑window discipline (≤2 wk, exactly one writer, backup + tested downgrade) |
| Permanent sole‑writer coordinator | Time‑boxed single‑writer rule per window; legacy coordinator between windows |
| Frozen schemas / no renames | Renames permitted in Phases 4‑6 (data‑preserving Alembic, frontend updated same phase) |
| Cross‑version LangGraph checkpoint migration tooling | Finish‑or‑restart (drain before schema migration, inventory shows ~1 h total finish cost) |
| Full rollback drills (production‑shaped data, parity metrics, alert thresholds) | Scaled‑down track: DB restore drill + checkpoint fixture replay + trace‑correlated smoke comparison |
| Full authorization contract tests (HTTP + agent + worker) | Deferred to Phase 4 exit gate (policy is mandatory; comprehensive testing waits until write redirection matters) |

All changes are documented in ADR‑0009 Sections 1‑3 and the options.md "Interview Decisions" block. **No silent removals detected.**

---

## BLOCKER Analysis

### BLOCKER #1 — Rollback credibility → **PRESERVED in time‑boxed form**

**Round‑3:** Old code can't read new rows/events/checkpoints after rollback. "Route rebinding" is not a rollback once persisted semantics change.

**Amendment effect:** Replaces with per‑window discipline: backup + tested Alembic downgrade per window, drain‑before‑migrate, no dual representations.

**Verdict:** The mechanism (backup + downgrade) is standard and **credible for the 2‑week window**. The decisive improvement is: you revert the *whole window*, not a single slice. There is no "old code interprets new rows" because you restore the old schema and its data.

**[WARN — Testing ordering gap]:** The exit gate says "test rollback with production‑shaped data" for Phase 4. This means the downgrade path is validated **during** the window, not before it. If a complex reshape migration (e.g. splitting one column into two with data transformation) has a broken downgrade, you discover it mid‑window under time pressure. **Fix before Phase 1:** change the Phase 4+ exit gate to require a *pre‑migration downgrade rehearsal* (what ADR‑0009 Sec 7 calls "executable compatibility test") as a precondition for the migration, not as a post‑migration validation.

---

### BLOCKER #2 — Authorization ownership → **RESOLVED**

**Round‑3:** No module‑level authz policy; no ActorContext; workers run with zero authorization.

**Amendment effect:** Amendment 1 / ADR‑0009 Sec 5 fully specifies context‑owned, deny‑by‑default ActorContext for ALL inbound adapters (HTTP, agents, workers, event consumers). Workers were confirmed by codebase verification to have no authorization — gap now closed normatively.

**Verdict:** The policy is complete and is **NOT scaled down** for pre‑production. The only deferral is comprehensive three‑entry‑point contract tests (moved to Phase 4 gate), not the implementation itself.

**[WARN — Latent multi‑actor gap]:** The "delayed destructive actions define whether authorisation is captured at command acceptance or revalidated at execution" requirement (ADR‑0009 Sec 5) is formally satisfied but practically meaningless for a single‑user system — the owner is the user, and revoking their own access is self‑defeating. When the system gains real users, every queued action's authz‑at‑execution model must be retrofitted. This is a **deferred‑not‑solved** item. **Fix before Phase 1:** Document this as a named assumption in the Phase 0 go/no‑go record so it is not forgotten.

---

### BLOCKER #3 — Shared‑table ownership → **RESOLVED**

**Round‑3:** Multiple modules can't independently write to `carousel_projects`. Need field‑level ownership and sole‑writer enforcement.

**Amendment effect:** Replaces permanent sole‑writer treaty with per‑migration‑window discipline (≤2 wk, exactly one writer per table, second‑module writes prohibited even inside the window). Field ownership map repurposed as migration map.

**Verdict:** Mechanically enforceable via Import Linter (only the permitted module imports the legacy table). Between windows, legacy coordinator remains sole writer (ADR‑0009 Sec 6). The window definition explicitly prohibits dual writers, which was the core hazard. **No gap — this is adequately preserved in time‑boxed form.**

---

## WARN Analysis

### WARN — Event delivery semantics → **PRESERVED**

Outbox design is normatively specified (ADR‑0009 Sec 8: PostgreSQL outbox, at‑least‑once, persistent dedup, stable IDs). Implementation sequenced to Phase 6. Phase 0 ships the reorder fix (persist + commit before Redis). The risk window between reorder fix and Phase 6 outbox (events can still be lost) is accepted for pre‑production. Adequate.

### WARN — LangGraph compatibility → **RESOLVED**

AE‑0075 confirmed PORTABLE serialization (0/6,918 checkpoints contain class‑path‑dependent payloads; 67,705 write blobs also clean). Finish‑or‑restart policy is safer than attempting cross‑version migration. Drain cost estimated at ~1 h. No remaining blocker.

### WARN — Concurrency policy → **RESOLVED**

Concurrency contract (7 fields) is drafted and decided. 409 conflict response is normative. Expected‑version enforcement extended in Phase 2.5 (now "extend existing service" rather than "build from scratch" per AE‑0075 correction). Appropriate staging.

### WARN — Pilot tests wrong risks → **RESOLVED**

Phase 2.5 explicitly exists to exercise the risks the Knowledge pilot cannot: shared‑row ownership, checkpoint compatibility, `lock_version` enforcement, duplicate‑command safety. Core deliverables address all identified gaps.

### WARN — Operational controls / observability → **WEAKENED (deliberately)**

Per‑slice SLI/alerting replaced by trace‑correlated smoke comparison. **This is appropriate for pre‑production** but the observability gap is real: if a user appears during Phase 3 or 4, regressions may go undetected. **Fix before Phase 1:** the Phase 0 risk register should explicitly name "What if a real user arrives before Phase 6?" as a contingency, with the answer "re‑evaluate track to `full` at the mid‑point go/no‑go."

### WARN — Estimates omit coexistence cost → **RESOLVED**

Revised estimate (11‑21 ew, ±15%), scope‑delta table, honest calendar (8‑14 months at 5‑10 h/wk), mid‑point go/no‑go, Phase 0 budget with overflow mechanism. This is credible.

### WARN — Adversarial tests missing → **PRESERVED**

Matrix skeleton is a Phase 0 deliverable. Per‑phase exit gates exercise rows incrementally. The "no descope" rule is recorded. Risk of schedule pressure overriding this is real but guardrailed.

---

## Pressure‑Test Specifics

### 1. Rollback with renames — credible or relabeled?

**Credible** under the per‑window model. Round‑3's core objection was "old code can't read new rows" — backup + downgrade avoids that problem by reverting the entire window's schema and data together. The gap is that **downgrade testing is not yet an executable precondition**; it's gated at phase exit, not at migration start. That's the WARN above.

### 2. Shared‑table enforcement — window discipline vs dual‑writer hazard

**Adequate.** The window definition (ADR‑0009 Sec 3) prohibits second‑module writes even inside the window. Between windows, the legacy coordinator is sole writer (Sec 6). Import Linter provides mechanical enforcement. No gap between windows — the policy is continuous.

### 3. Authz — pre‑production justification overused?

**Not overused for the current scope.** The ActorContext requirement is NOT scaled down — it applies to every entry point. Only the *comprehensive testing* is deferred. The latent multi‑actor gap (retrofitting authz‑at‑execution for queued actions) is real but manageable if documented. Named as a WARN above.

### 4. Drain‑before‑migrate ordering — interleavings missed?

One gap: **mid‑execution checkpoints** (those not at a LangGraph `interrupt()` point) during a code swap. The plan assumes checkpoints are at safe points, which is true for LangGraph interrupts but not for in‑progress LLM calls or agent steps. If the application is stopped during a non‑interrupted execution, that checkpoint's state is lost. **Fix before Phase 1:** add a note that drain applies only to checkpoints at SAFE points (interrupts), and non‑interrupted executions are terminated on deployment. Document the (tiny) loss risk for pre‑production.

### 5. AE‑0075 downgrade — safe?

**Safe.** 0/6,918 checkpoints contain `rag_backend` class paths. The finished‑or‑restart policy handles any false negatives gracefully. The PORTABLE evidence is the strongest possible signal.

### 6. Silent removals?

**None detected.** Every round‑3 concern is mapped to a corresponding ADR section or explicit deferral. The round‑2 and round‑3 decision logs in options.md show disposition and closure criteria for every finding.

### 7. Pre‑production justification overused?

**Appropriate** with one named risk: **event loss until Phase 6 if a real user arrives early.** The reorder fix prevents the worst inconsistency (publish‑before‑commit), but without a durable outbox, events can still be lost in a crash between commit and Redis publish. The ADR should note: "if a real user arrives before Phase 6, the outbox timeline SHALL accelerate." Currently this is implicit.

---

## Findings Summary

| # | Category | Round‑3 Concern | Verdict | Phase 1 Impact |
|---|---|---|---|---|
| **F1** | Rollback | Credibility with renames | **[WARN]** — downgrade testing is post‑migration, not a precondition | Test ordering gap must be closed before Phase 4, not before Phase 1 |
| **F2** | Authz | Latent multi‑actor gap | **[WARN]** — queued‑action authz retrofits required when real users arrive | Document as named assumption in Phase 0 risk record |
| **F3** | Drain | Non‑interrupted checkpoint loss | **[WARN]** — mid‑execution checkpoints may be dropped; not explicitly addressed | Add SAFE‑point caveat to Phase 0 checkpoint inventory deliverables |
| **F4** | Observability | Real‑user arrival before Phase 6 | **[WARN]** — event loss window exists until outbox ships | Add contingency rule to Phase 0 risk register |
| **F5** | Shared table | Window enforcement | **[OK-RESOLVED]** — adequately preserved | None |
| **F6** | Authz policy | ActorContext + deny‑by‑default | **[OK-RESOLVED]** — fully specified | None |
| **F7** | Checkpoint portability | AE‑0075 downgrade | **[OK-RESOLVED]** — PORTABLE evidence robust | None |
| **F8** | Concurrency | 409 / idempotency / lock_version | **[OK-RESOLVED]** — designed and staged | None |
| **F9** | Pilot risk | Phase 2.5 mitigates | **[OK-RESOLVED]** | None |
| **F10** | Estimates | Revised, go/no‑go | **[OK-RESOLVED]** | None |
| **F11** | Adversarial tests | Matrix designed, phased | **[OK-RESOLVED]** | None |
| **F12** | Silent removals | None found | **[OK-RESOLVED]** | None |

---

## Residual Risks for Proceeding to Phase 1

1. **Undiscovered downgrade failures** for complex reshape migrations — mitigated by per‑window discipline, but the downgrade test ordering gap means the first rename migration may extend beyond 2 weeks if the reversal is broken.
2. **Event loss between reorder fix and Phase 6 outbox** — acceptable for pre‑production; becomes a problem if a real user arrives mid‑plan.
3. **Authz test coverage deferred to Phase 4** — a bypass discovered during Phases 2‑3 would require emergency out‑of‑phase remediation.
4. **Mid‑execution checkpoint loss on deployment** — in‑progress LLM calls terminated by a code swap are silently discarded. Acceptable for pre‑production with trivial workflows.
5. **Single‑user justification masking real multi‑user requirements** — every deferral has an implicit timeline that may not hold if adoption outpaces the plan.
6. **Schedule pressure** — 8‑14 months at 5‑10 h/wk is a long commitment; motivation drift or feature pressure could cause testing/policy compliance to erode despite safeguards.

**None of these risks block Phase 1.** Phase 1 is architecture scaffolding only — package roots, Import Linter contracts, CI jobs, no behavior moves, no schema changes, no write redirection. All four WARNs (F1‑F4) must be addressed **before Phase 4** (first write redirection), and their documentation should land in Phase 0, not Phase 1.

---

## Required Fixes Before Phase 4 (not Phase 1)

| Finding | Fix | Owner | Deadline |
|---|---|---|---|
| F1 — Downgrade test ordering | Phase 4+ exit gate: downgrade rehearsal is a *pre‑migration* precondition, not a post‑migration validation | Phase 0 / ADR‑0009 amendment | Before Phase 4 migration |
| F2 — Multi‑actor authz | Document "queued‑action authz is self‑defeating for single user; retrofitted at multi‑actor milestone" in Phase 0 risk record | Phase 0 deliverable | Before first multi‑actor gate |
| F3 — Mid‑execution checkpoint loss | Add SAFE‑point caveat to checkpoint drain rule: applies to interrupt‑point checkpoints only; non‑interrupted executions are terminated on deployment | Phase 0 / drain‑before‑migrate definition | Before Phase 4 |
| F4 — Real‑user before Phase 6 | Add contingency: "if a real user appears before Phase 6, outbox timeline SHALL accelerate; mid‑point go/no‑go shall re‑evaluate the track" | Phase 0 risk register | Before first user arrival |

**None of the above are Phase 1 blockers.**

---

## One‑Line Human Verdict

**PROCEED_WITH_CAUTION** — Phase 1 is safe to start; all four WARNs are Phase 4 blockers, not Phase 1 blockers, and each has a documented fix.

QA_VERDICT: WARN
