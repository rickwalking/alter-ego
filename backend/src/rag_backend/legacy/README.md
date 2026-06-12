# legacy/ — Pre-Migration Coordinators

**Purpose:** home for the pre-migration coordinators that remain during the
modular-monolith migration.

Per [ADR-0009](../../../../../docs/decisions/0009-adopt-domain-modular-monolith.md)
§6, while `carousel_projects` remains shared persistence, the
`legacy.carousel_project` coordinator is the **sole write owner** of that table
and applies row changes through a single legacy Unit of Work that owns
`lock_version`. New modules return decisions/results to this coordinator rather
than writing the shared row themselves.

## Status

Empty root. AE-0080 establishes the package only (scaffolding). The legacy
coordinators are relocated here in later migration phases. No code lives here
yet.
