# Cold Critic Review

## Verdict
BLOCK

## Findings

### [BLOCKER] Rollback is not credible once transactional behavior changes
- Assumption: Route rebinding alone can revert each migration slice.
- Risk: Introducing a request-scoped Unit of Work, outbox records, projections, and new transaction boundaries changes persisted state and side effects even while legacy tables remain authoritative.
- Impact: A rollback could replay events, lose committed work, expose stale projections, or return control to legacy handlers that interpret rows differently.
- Suggested mitigation: Define per-phase compatibility invariants, rollback windows, event fencing, outbox handling, and forward-fix procedures. Demonstrate rollback with production-shaped data before redirecting traffic.
- Open question for author: What exact persisted artifacts can each phase create, and how will legacy code safely interpret or ignore them after rollback?

### [BLOCKER] Authorization ownership is underspecified across contexts
- Assumption: Identity contracts plus preserved owner/reviewer checks are sufficient to maintain authorization.
- Risk: Authentication is assigned to `identity`, while project ownership, reviewer assignments, publication visibility, document access, and conversation access belong to other modules. The plan does not define where resource-level authorization decisions occur or how they are enforced consistently across HTTP, agents, workers, and event consumers.
- Impact: Migration could create privilege escalation, cross-tenant data access, or background actions performed without current authorization.
- Suggested mitigation: Specify an authorization model covering tenant boundaries, resource policies, actor propagation, service identities, revoked access, and event-consumer authorization. Add deny-by-default contract tests for every inbound adapter.
- Open question for author: Which module decides whether an actor may read, mutate, publish, or invoke AI against a specific resource?

### [BLOCKER] Shared-table ownership conflicts with claimed module boundaries
- Assumption: Multiple modules can derive independent aggregates from `carousel_projects` while that row remains the single write authority.
- Risk: Editorial, presentation, and publishing concepts may share columns, invariants, version numbers, and lifecycle transitions in one row. A compatibility repository cannot create independent ownership if commands still contend over the same persistence model.
- Impact: Lost updates, accidental invariant coupling, oversized transactions, and changes in one module silently corrupting another module's interpretation.
- Suggested mitigation: Produce a field-level ownership map, transition ownership table, concurrency-token policy, and explicit rule for commands that affect more than one proposed aggregate.
- Open question for author: Who owns the row version and transaction when one operation changes editorial status, presentation artifacts, and publication metadata together?

### [WARN] Event delivery semantics are asserted rather than designed
- Assumption: PostgreSQL outbox plus Redis and idempotent consumers provides reliable asynchronous integration.
- Risk: The plan does not define relay concurrency, ordering, duplicate detection, retry limits, poison events, retention, schema evolution, or Redis-loss recovery. "Consumers are idempotent" is not an actionable guarantee.
- Impact: Duplicate publishing, missed projections, events processed out of order, or permanently stalled consumers.
- Suggested mitigation: Define delivery guarantees, aggregate ordering rules, stable event IDs, deduplication persistence, dead-letter operations, replay procedures, and compatibility rules before the first production event.
- Open question for author: Is Redis a notification transport over a durable PostgreSQL outbox, or is successful Redis publication treated as delivery completion?

### [WARN] LangGraph compatibility has no validated state migration strategy
- Assumption: Preserving checkpoint identifiers and schemas is enough to keep active workflows resumable.
- Risk: Physical code movement, handler changes, renamed nodes, altered serialization types, dependency wiring, or changed transaction timing can invalidate in-flight checkpoints without changing their identifiers.
- Impact: Existing workflows may fail on resume, repeat externally visible actions, or become permanently stranded.
- Suggested mitigation: Inventory deployed checkpoint versions and create replay/resume compatibility tests using captured production-shaped states. Version workflow definitions and specify behavior for checkpoints created by older releases.
- Open question for author: Can old and new application versions resume every currently persisted checkpoint safely during rolling deployment and rollback?

### [WARN] Concurrency policy is incomplete
- Assumption: "Optimistic locking behind editorial ports" and one Unit of Work per command address concurrency.
- Risk: There is no policy for SSE commands, workflow workers, retries, simultaneous editorial and presentation updates, or outbox consumers operating on the same legacy row. Read-only sessions also do not guarantee projection freshness.
- Impact: Lost updates, duplicate artifact builds, stale approvals, and publication based on superseded content.
- Suggested mitigation: Define aggregate concurrency boundaries, expected-version contracts, command idempotency keys, lock-conflict behavior, and freshness requirements for each user-visible read model.
- Open question for author: Which operations require serial execution, and what response does the client receive on a version conflict?

### [WARN] The pilot may validate the wrong risks
- Assumption: Knowledge is representative enough to validate the modularization approach before authorizing the carousel split.
- Risk: Knowledge exercises adapters and repositories but may not exercise the hardest issues: shared-row ownership, long-running workflows, checkpoint compatibility, cross-context authorization, artifact side effects, and multi-actor concurrency.
- Impact: A successful pilot could create false confidence while leaving the principal migration risks untested.
- Suggested mitigation: Keep Knowledge as the scaffolding pilot, but require a narrow workflow checkpoint and shared-row compatibility spike before approving Phases 4-6.
- Open question for author: Which pilot acceptance test demonstrates that the approach works for the legacy carousel aggregate rather than only for a cohesive subsystem?

### [WARN] Operational controls and observability are not specified enough
- Assumption: Feature flags, architecture reports, and legacy-versus-new usage metrics make slices operationally safe.
- Risk: There are no named service-level indicators, alert thresholds, correlation identifiers, shadow comparison rules, flag ownership, or deployment-order constraints.
- Impact: Semantic regressions may remain invisible until users report them; mixed-version deployments could process incompatible events or state.
- Suggested mitigation: Define per-slice parity metrics, error and latency budgets, trace propagation, deployment ordering, flag lifecycle, and automated rollback criteria.
- Open question for author: What measurable signal proves that a redirected endpoint is behaviorally equivalent and safe to keep enabled?

### [WARN] Estimates omit substantial coexistence cost
- Assumption: One senior engineer can complete the plan in 8-14 engineer-weeks while preserving behavior and coexisting with AE-0040.
- Risk: The estimate appears to include extraction work but not enough allowance for production-data analysis, authorization review, checkpoint fixtures, event operations, dual-path observability, rollback drills, frontend contract reconciliation, and merge conflicts.
- Impact: Schedule pressure may cause temporary adapters and exceptions to become permanent or force phases to ship without adequate verification.
- Suggested mitigation: Estimate discovery, coexistence, verification, and cleanup separately. Track temporary compatibility code and CI exceptions as explicit liabilities with owners and deadlines.
- Open question for author: What historical delivery data or codebase inventory supports the phase durations?

### [WARN] Test strategy misses destructive and adversarial cases
- Assumption: Existing Gherkin scenarios, repository contracts, ORM round trips, and OpenAPI drift checks protect behavior.
- Risk: These tests do not inherently cover authorization bypass, duplicate commands, concurrent updates, transaction cancellation, event replay, partial vendor failure, stale projections, rolling deployments, or old checkpoint resumption.
- Impact: Tests may pass while production behavior regresses under failure or load.
- Suggested mitigation: Add failure-injection, concurrency, migration, rollback, security-policy, event-replay, and mixed-version compatibility suites tied to phase exit gates.
- Open question for author: Which tests verify exactly-once business effects despite at-least-once command or event execution?

## Missing evidence
- Contents and constraints of ADR-001 through ADR-008.
- Current schema, migration history, and field-level use of `carousel_projects`.
- Existing transaction, session, tenant, and authorization models.
- LangGraph checkpoint schemas and examples of active persisted states.
- Current Redis durability and worker topology.
- Production traffic, data volume, workflow duration, and concurrency characteristics.
- API/SSE compatibility inventory, including undocumented client dependencies.
- Failure-mode analysis for external AI, vector, rendering, storage, and publishing vendors.
- Baseline test coverage and evidence that the proposed CI ratchets cannot be bypassed.
- Operational ownership for outbox replay, dead letters, flags, and rollback decisions.

## Residual risks if plan proceeds unchanged
- Security boundaries may diverge between routes, agents, workers, and consumers.
- Shared-table coupling may survive behind cleaner package boundaries.
- In-flight workflows may become non-resumable across deployment or rollback.
- Duplicate or reordered events may cause irreversible external side effects.
- Temporary compatibility layers and import exceptions may become permanent.
- The Knowledge pilot may pass without reducing the principal carousel migration risk.
- The stated schedule may incentivize incomplete testing and premature legacy removal.

## Review provenance

- Reviewer: separate ephemeral `codex exec` session
- Reviewer workspace: `/tmp`
- Sandbox: read-only
- Input: cold-critic system prompt plus plan-only blind packet
- Repository access: not provided
- Session: `019eb7df-870c-7f01-a6cd-7099ec2efc63`
- Date: 2026-06-11
