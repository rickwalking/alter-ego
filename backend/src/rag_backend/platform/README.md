# platform/ — Shared Technical Concerns

**Purpose:** cross-cutting technical infrastructure shared by all bounded
contexts — not business logic.

Per [ADR-0009](../../../../../docs/decisions/0009-adopt-domain-modular-monolith.md)
§9, this is where shared technical services live: database / unit-of-work
plumbing, messaging and the Phase 6 outbox transport, configuration, logging,
telemetry, and the `PlatformServices` object passed into each module's
`bootstrap_module(platform: PlatformServices)`.

## What belongs here

- Shared technical adapters and plumbing reused across contexts
- The `PlatformServices` aggregate (later phases)

## What does NOT belong here

- Domain or business logic of any bounded context
- Composition-root wiring (that lives in `bootstrap/`)

## Status

Empty root. AE-0080 establishes the package only (scaffolding). Shared concerns
are migrated here in later phases.
