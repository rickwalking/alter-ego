# modules/ — Bounded Contexts

**Purpose:** home for the bounded-context packages of the modular monolith.

Per [ADR-0009](../../../../../docs/decisions/0009-adopt-domain-modular-monolith.md),
each bounded context (editorial, carousel presentation, publishing, knowledge,
conversation, persona, quality, identity, editorial operations) becomes a
subpackage here with its own internal layers, public contract, ports, and
adapters. Context names resolve against
[`docs/architecture/domain-glossary.md`](../../../../../docs/architecture/domain-glossary.md)
(AE-0071).

## Status

Empty root. AE-0080 establishes the package only (scaffolding). The shared
`modules/_template/` arrives in **AE-0081**; individual contexts are carved out
in later migration phases. No business logic lives here yet.
