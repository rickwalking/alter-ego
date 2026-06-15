"""Bounded-context modules for the Alter-Ego backend.

Each subpackage here is a bounded context (e.g. editorial, carousel
presentation, publishing, knowledge, conversation, persona, quality,
identity, editorial operations) with its own internal layers, public
contract, ports, and adapters, per ADR-0009 (Domain Modular Monolith).

This package is currently an empty root — bounded contexts are carved out
in later migration phases. No business logic is moved here in AE-0080
(scaffolding only). The shared module template arrives in AE-0081.

See ``docs/decisions/0009-adopt-domain-modular-monolith.md`` and
``docs/architecture/domain-glossary.md``.
"""
