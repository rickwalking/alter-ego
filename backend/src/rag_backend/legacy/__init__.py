"""Pre-migration coordinators for the Alter-Ego backend.

This package will hold the pre-migration coordinators that remain during the
modularization — most notably the ``legacy.carousel_project`` coordinator that
is the **sole write owner** of the shared ``carousel_projects`` table while it
remains shared persistence, per ADR-0009 (Domain Modular Monolith) §6.

This package is currently an empty root. Coordinators are relocated here in
later migration phases. No code is moved here in AE-0080 (scaffolding only).

See ``docs/decisions/0009-adopt-domain-modular-monolith.md`` §6.
"""
