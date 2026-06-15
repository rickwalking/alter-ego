"""Composition root for the identity module — manual constructor injection.

``bootstrap_module`` wires the identity application services to their
collaborators explicitly. There is no DI framework and no global container
lookup inside the module (ADR-0009 §9) — the inbound edge constructs the
request-scoped collaborators (the ``UserRepository`` enlisted in the request's
Unit of Work and the ``Settings`` carrying the JWT secret/expiry) and passes
them in.

**Behavior-preserving wiring (AE-0098).** JWT/bcrypt are NOT reimplemented or
relocated: the bootstrap builds the thin ``infrastructure/auth_adapters``
(``BcryptPasswordHasher`` / ``JwtTokenIssuer``) over the UNCHANGED
``infrastructure.auth`` functions and injects them into the services. The
collaborators are accepted via the typed :class:`IdentityAdapters` bundle so the
function keeps to a single grouped argument (backend/CLAUDE.md ≤3 args).

The ``PlatformServices`` protocol is a local placeholder (as in the reference
template) so the module is importable and type-clean before
``rag_backend.platform`` ships. A real module reads database/session factories
and telemetry from it to build adapters here once it exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.identity.application.authentication_service import (
    AuthenticationDeps,
    AuthenticationService,
)
from rag_backend.modules.identity.application.password_service import PasswordService
from rag_backend.modules.identity.application.user_service import (
    UserService,
    UserServiceDeps,
)
from rag_backend.modules.identity.domain.ports import UserRepository
from rag_backend.modules.identity.infrastructure.auth_adapters import (
    BcryptPasswordHasher,
    JwtTokenIssuer,
)
from rag_backend.platform.database import UnitOfWork


class PlatformServices(Protocol):
    """Placeholder for the shared platform substrate passed to bootstrap.

    Replaced by ``rag_backend.platform.PlatformServices`` once it exists.
    """


@dataclass(frozen=True)
class IdentityAdapters:
    """Pre-constructed, request-scoped collaborators for the identity module.

    Built at the inbound edge (the api adapter / legacy route) from the existing
    infrastructure so the module wires to them without relocation (AE-0098). The
    ``unit_of_work`` wraps that same request's ``AsyncSession`` and is the single
    transaction owner the user service commits through (ADR-0009 §9); ``settings``
    carries the unchanged JWT secret/expiry used to issue and validate tokens.
    """

    repository: UserRepository
    settings: Settings
    unit_of_work: UnitOfWork


@dataclass(frozen=True)
class IdentityServices:
    """The identity module's public application services (the wired result)."""

    users: UserService
    authentication: AuthenticationService
    passwords: PasswordService


def bootstrap_module(
    platform: PlatformServices,
    adapters: IdentityAdapters,
) -> IdentityServices:
    """Wire the identity module and return its public application services.

    ``platform`` is accepted to demonstrate the ADR-0009 §9 bootstrap signature
    (a real module builds adapters from it once ``rag_backend.platform`` ships).
    For the behavior-preserving phase the caller supplies the already-built
    request-scoped collaborators via ``adapters``; this function constructs the
    bcrypt/JWT adapters over the unchanged ``infrastructure.auth`` and injects
    everything into the services via their constructors.
    """
    _ = platform  # real modules construct adapters from platform services
    passwords = PasswordService(hasher=BcryptPasswordHasher())
    tokens = JwtTokenIssuer(adapters.settings)
    users = UserService(
        repository=adapters.repository,
        deps=UserServiceDeps(
            passwords=passwords,
            unit_of_work=adapters.unit_of_work,
        ),
    )
    authentication = AuthenticationService(
        repository=adapters.repository,
        deps=AuthenticationDeps(passwords=passwords, tokens=tokens),
    )
    return IdentityServices(
        users=users,
        authentication=authentication,
        passwords=passwords,
    )


__all__ = [
    "IdentityAdapters",
    "IdentityServices",
    "bootstrap_module",
]
