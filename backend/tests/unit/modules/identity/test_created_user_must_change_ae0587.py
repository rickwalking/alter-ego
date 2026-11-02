"""Users an admin creates are flagged to change the password; others are not.

Scenarios: ``tests/features/force_change_for_created_users_ae0587.feature``.
The admin handler and user service run over the identity test doubles, whose
repository only persists on a Unit of Work commit. The bootstrap owner script
runs against a throwaway SQLite file.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.modules.identity import (
    CreateUserCommand,
    CreateUserInput,
    User,
    UserAlreadyExistsError,
)
from rag_backend.scripts import bootstrap_admin as bootstrap_script
from tests.unit.modules.identity import test_identity_services as services
from tests.unit.modules.identity.test_identity_handlers import (
    _HASH_PREFIX,
    _VALID_PASSWORD,
    _build_admin_handler,
    _seed_user,
)

_NEW_EMAIL = "created@example.com"
_OWNER_EMAIL = "owner@example.com"
_TYPED_PASSWORD = "AdminChosenPass123!"


def _create_input(password: str | None = None) -> CreateUserInput:
    return CreateUserInput(
        email=_NEW_EMAIL, full_name="Created User", role="editor", password=password
    )


@pytest.mark.unit
class TestAdminCreateFlagsTheUser:
    """``AdminUserHandler.create`` flags every user it creates."""

    # Scenario: A user created with a generated password must change it
    async def test_a_generated_password_flags_the_user(self) -> None:
        handler, repo, uow = _build_admin_handler()

        created = await handler.create(_create_input())

        assert created.temp_password is not None
        stored = await repo.get_by_id(created.id)
        assert stored is not None
        assert stored.must_change_password is True
        assert stored.hashed_password == _HASH_PREFIX + created.temp_password
        assert uow.commits == 1

    # Scenario: A user created with a password the admin typed must change it too
    async def test_a_typed_password_flags_the_user_too(self) -> None:
        handler, repo, _ = _build_admin_handler()

        created = await handler.create(_create_input(_TYPED_PASSWORD))

        assert created.temp_password is None
        stored = await repo.get_by_id(created.id)
        assert stored is not None
        assert stored.must_change_password is True
        assert stored.hashed_password == _HASH_PREFIX + _TYPED_PASSWORD

    # Scenario: A refused create flags nobody
    async def test_a_duplicate_email_writes_nothing(self) -> None:
        handler, repo, uow = _build_admin_handler()
        existing = _seed_user(repo, email=_NEW_EMAIL)

        with pytest.raises(UserAlreadyExistsError):
            await handler.create(_create_input())

        assert uow.commits == 0
        assert list(repo.persisted) == [existing.id]
        assert existing.must_change_password is False


@pytest.mark.unit
class TestOtherCreatePathsDoNotFlag:
    """Users created outside the admin create flow keep the flag off."""

    # Scenario: Users created outside the admin create flow are not flagged
    async def test_the_user_service_does_not_flag(self) -> None:
        service, repo, _ = services._build_user_service()

        view = await service.create(
            CreateUserCommand(
                email=_NEW_EMAIL, full_name="Service User", password=_VALID_PASSWORD
            )
        )

        stored = await repo.get_by_id(view.id)
        assert stored is not None
        assert stored.must_change_password is False

    # Scenario: Users created outside the admin create flow are not flagged
    async def test_the_bootstrap_owner_is_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'boot.db'}")
        async with engine.begin() as conn:
            await conn.run_sync(db_config.Base.metadata.create_all)

        async def _use_engine(
            _url: str, pool_size: int = 5, max_overflow: int = 10
        ) -> None:
            monkeypatch.setattr(db_config, "c_engine", engine)

        async def _keep_engine() -> None:
            return None

        monkeypatch.setattr(bootstrap_script, "init_db", _use_engine)
        monkeypatch.setattr(bootstrap_script, "close_db", _keep_engine)
        try:
            await bootstrap_script.bootstrap_admin(_OWNER_EMAIL, "Owner")
            owner = await _stored_by_email(_OWNER_EMAIL)
        finally:
            await engine.dispose()

        assert owner is not None
        assert owner.must_change_password is False


async def _stored_by_email(email: str) -> User | None:
    from rag_backend.infrastructure.database.user_repository import (
        PostgresUserRepository,
    )

    async with db_config.get_session_maker()() as session:
        return await PostgresUserRepository(session).get_by_email(email)
