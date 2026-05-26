"""Bootstrap the first admin user via CLI.

Usage:
    cd backend && uv run python -m rag_backend.scripts.bootstrap_admin --email admin@example.com --full-name "Admin User"

This script creates the first admin user if no users exist in the database.
It is intended for one-time initial setup only.
"""

import argparse
import asyncio
import sys

from rag_backend.domain.models import User, UserRole
from rag_backend.infrastructure.auth import hash_password
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import close_db, init_db
from rag_backend.infrastructure.database.user_repository import PostgresUserRepository


def _generate_temp_password(length: int = 16) -> str:
    """Generate a secure temporary password."""
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%^&*" for c in password)
        ):
            return password


async def bootstrap_admin(email: str, full_name: str) -> None:
    """Create the first admin user if the database has no users.

    Args:
        email: Admin email address.
        full_name: Admin full name.

    Raises:
        SystemExit: If users already exist or on database error.
    """
    settings = get_settings()

    try:
        await init_db(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
        )

        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from rag_backend.infrastructure.database.config import c_engine

        session_maker = async_sessionmaker(
            c_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with session_maker() as session:
            repo = PostgresUserRepository(session)

            # Check if any users exist
            count = await repo.count()
            if count > 0:
                print(
                    "ERROR: Users already exist in the database. Bootstrap is only for initial setup.",
                    file=sys.stderr,
                )
                sys.exit(1)

            temp_password = _generate_temp_password()

            admin = User(
                email=email,
                full_name=full_name,
                hashed_password=hash_password(temp_password),
                role=UserRole.ADMIN,
                is_active=True,
            )

            created = await repo.create(admin)
            await session.commit()

            print("Admin user created successfully!")
            print(f"  ID:       {created.id}")
            print(f"  Email:    {created.email}")
            print(f"  Name:     {created.full_name}")
            print(f"  Role:     {created.role.value}")
            print(f"  Password: {temp_password}")
            print("")
            print("IMPORTANT: Save this password. It will not be displayed again.")

    except Exception as e:
        print(f"ERROR: Failed to bootstrap admin: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await close_db()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Bootstrap the first admin user")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--full-name", required=True, help="Admin full name")
    args = parser.parse_args()

    asyncio.run(bootstrap_admin(args.email, args.full_name))


if __name__ == "__main__":
    main()
