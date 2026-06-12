# Phase 0 Risk Register — deferred items from the migrate-in-place delta review

**Source:** cold-critic delta skeptical review of the scaled-down + migrate-in-place
amendment (2026-06-12). Full review: `.agent/reports/domain-modularization.delta-review.md`.
**Verdict:** PROCEED_WITH_CAUTION — Phase 1 (architecture scaffolding) is safe to start;
the items below are **pre-Phase-4 obligations** (first write redirection), recorded here in
Phase 0 so they are not lost. None block Phase 1.

The migrate-in-place amendment was found to **over-remove nothing silently**: the three
round-3 BLOCKERs are RESOLVED (authorization ownership, shared-table ownership) or
PRESERVED in time-boxed form (rollback credibility). The four items below are residual
WARNs whose fixes have a deadline later than Phase 1.

## Required amendments before Phase 4

| ID | Risk | Required fix | Deadline | Lands in |
|----|------|--------------|----------|----------|
| **F1** | Downgrade testing is gated at phase *exit*, so a broken reversal of a complex reshape migration (e.g. one column → two with transformation) is discovered mid-window under time pressure. | Make a **pre-migration downgrade rehearsal** an explicit *precondition* for any schema-modifying migration in the Phase 4+ exit gates (ADR-0009 §7 "executable compatibility test"), not a post-migration validation. | Before Phase 4 | ADR-0009 §7 + plan Phase 4+ exit gate |
| **F2** | Authorization policy (ActorContext, deny-by-default) is fully specified and NOT scaled down, but comprehensive 3-entry-point contract tests are deferred to Phase 4, and the "authz captured at command acceptance vs revalidated at execution" rule is practically moot for a single user — it must be retrofitted for queued/delayed destructive actions once real users exist. | Record as a **named assumption**: "queued-action authz-at-execution is self-defeating for a single user; retrofit at the first multi-actor milestone." Re-open authz contract-test scope at that milestone. | Before first multi-actor gate | this register (named) + Phase 4 authz tests |
| **F3** | Drain-before-migrate assumes checkpoints sit at LangGraph `interrupt()` points. A code swap during a **non-interrupted** execution (in-progress LLM call / agent step) silently discards that checkpoint's state. | Add a **SAFE-point caveat** to the drain rule: drain applies to interrupt-point checkpoints only; non-interrupted executions are terminated on deployment, with the (tiny, pre-prod) loss risk documented. | Before Phase 4 | ADR-0009 §3 drain rule + checkpoint inventory note |
| **F4** | No durable outbox until Phase 6, so events can be lost on a crash between commit and Redis publish (the Phase-0 reorder fix only prevents publish-before-commit). Per-slice SLI/alerting was scaled down to trace-correlated smoke comparison — regressions may go undetected if a real user arrives mid-plan. | Add a **contingency rule**: "if a real user appears before Phase 6, the outbox timeline SHALL accelerate and the mid-point go/no-go SHALL re-evaluate the track (scaled-down → full)." | Before first user arrival | ADR-0009 §8 + mid-point go/no-go |

## Residual risks accepted for Phase 1 → Phase 3 (pre-write-redirection)

1. Undiscovered downgrade failures for complex reshape migrations (mitigated by per-window discipline; F1 closes the test-ordering gap before Phase 4).
2. Event loss between the reorder fix and the Phase 6 outbox — acceptable pre-production (F4 contingency if a user arrives).
3. Authz contract-test coverage deferred to Phase 4 — a bypass found in Phases 2-3 would need out-of-phase remediation.
4. Mid-execution checkpoint loss on deployment — acceptable pre-production with trivial workflows (F3).
5. Single-user justification masking real multi-user requirements — every deferral has an implicit timeline (tracked at the mid-point go/no-go).
6. Schedule erosion over 8-14 months at 5-10 h/week — guardrailed by the "no-descope" testing rule and per-phase exit gates.

## Disposition

- **Phase 1 may proceed.** It is scaffolding only — package roots, Import Linter contracts,
  CI jobs — with no behavior moves, schema changes, or write redirection, so none of
  F1-F4 apply yet.
- F1-F4 must be actioned **before Phase 4**; F2/F4 also gate the first real-user milestone.
- Re-check this register at the **mid-point (Phase-3 / month-6) go/no-go**.
