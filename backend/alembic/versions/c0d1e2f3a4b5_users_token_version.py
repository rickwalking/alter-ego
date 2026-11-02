"""users token_version

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-11-01

Additive: one integer column on ``users``, NOT NULL with a server default of
0, so every existing user starts at version 0 and the access tokens issued
before it (no ``tv`` claim, read as 0) keep working. On Postgres 11+ a
constant default is stored in the catalog, so no row is rewritten. Idempotent
so a database that already has the column is left alone; a database without a
``users`` table (partial schemas some migration tests stamp) is left alone too.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None

_TABLE = "users"
_COLUMN = "token_version"


def _has_table() -> bool:
    return bool(sa.inspect(op.get_bind()).has_table(_TABLE))


def _has_column() -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(_TABLE)
    return any(column["name"] == _COLUMN for column in columns)


def upgrade() -> None:
    """Add ``users.token_version`` when the table lacks it."""
    if not _has_table() or _has_column():
        return
    op.add_column(
        _TABLE,
        sa.Column(_COLUMN, sa.Integer(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    """Drop ``users.token_version``."""
    if _has_table() and _has_column():
        op.drop_column(_TABLE, _COLUMN)
