from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = None


def get_target_metadata():
    """Get target metadata from all models."""
    from rag_backend.infrastructure.database.models.blog_post import (
        BlogPostModel,
        BlogPostModelError,
        BlogPostStatus,
    )
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
        CarouselSlideModel,
        ResearchSourceModel,
    )
    from rag_backend.infrastructure.database.models.conversation import (
        ConversationModel,
        MessageModel,
    )
    from rag_backend.infrastructure.database.models.document import DocumentModel
    from rag_backend.infrastructure.database.models.persona_rubric import (
        PersonaProfileModel,
        QualityRubricModel,
        RubricEvaluationScoreModel,
    )
    from rag_backend.infrastructure.database.models.source_comment import (
        ContentSourceModel,
        ContentVersionModel,
        EditorialCommentModel,
    )
    from rag_backend.infrastructure.database.models.user import UserModel

    models = [
        BlogPostModel,
        BlogPostStatus,
        BlogPostModelError,
        CarouselProjectModel,
        CarouselSlideModel,
        ResearchSourceModel,
        PersonaProfileModel,
        QualityRubricModel,
        RubricEvaluationScoreModel,
        ContentSourceModel,
        ContentVersionModel,
        EditorialCommentModel,
        ConversationModel,
        MessageModel,
        DocumentModel,
        UserModel,
    ]

    return {m.__table__.name: m.__table__ for m in models if hasattr(m, '__table__')}


target_metadata = get_target_metadata()


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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
