"""Shared technical platform for the Alter-Ego backend.

This package will hold cross-cutting technical concerns shared by all bounded
contexts (e.g. database/unit-of-work plumbing, messaging/outbox transport,
configuration, logging, telemetry, and the ``PlatformServices`` passed to each
module's ``bootstrap_module()``), per ADR-0009 (Domain Modular Monolith).

This package is currently an empty root. No business or domain logic belongs
here — only shared technical infrastructure. No code is moved here in AE-0080
(scaffolding only).

See ``docs/decisions/0009-adopt-domain-modular-monolith.md`` §9.
"""
