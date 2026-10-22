import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_target_metadata():
    """Get target metadata from all registered ORM models."""
    import rag_backend.infrastructure.database.models  # noqa: F401
    from rag_backend.infrastructure.database.config import Base

    return Base.metadata


target_metadata = get_target_metadata()


def migration_database_url() -> str:
    """Resolve a sync SQLAlchemy URL for Alembic from DATABASE_URL."""
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = migration_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        migration_database_url(), poolclass=pool.NullPool, hide_parameters=True
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
