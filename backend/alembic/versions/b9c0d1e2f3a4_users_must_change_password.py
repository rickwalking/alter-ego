"""users must_change_password

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-10-31

Additive: one boolean column on ``users``, NOT NULL with a server default of
false, so every existing user keeps signing in normally. On Postgres 11+ a
constant default is stored in the catalog, so no row is rewritten. Idempotent
so a database that already has the column is left alone.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None

_TABLE = "users"
_COLUMN = "must_change_password"


def _has_column() -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(_TABLE)
    return any(column["name"] == _COLUMN for column in columns)


def upgrade() -> None:
    """Add ``users.must_change_password`` when missing."""
    if _has_column():
        return
    op.add_column(
        _TABLE,
        sa.Column(
            _COLUMN, sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )


def downgrade() -> None:
    """Drop ``users.must_change_password``."""
    if _has_column():
        op.drop_column(_TABLE, _COLUMN)
