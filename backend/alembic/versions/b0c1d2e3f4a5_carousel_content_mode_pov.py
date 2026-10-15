"""carousel content mode and pov inputs; creator asset role and pose

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-10-15

AE-0373 (ADR-0021): ADDITIVE. ``carousel_projects`` gains the content mode
(NULL = Radar IA, ``news_analysis``) and the "Ponto de Vista" inputs: thesis,
personal proof, format, slide count, CTA goal, the chosen hook and the slide-1
photo (FK to ``carousel_creator_assets``, SET NULL on delete).
``carousel_creator_assets`` gains ``role`` (hook / cta / pov) and ``pose_tag``.
Every column is nullable; no existing column is altered or dropped, so the
LangGraph checkpoint-drain rule does not apply. ``downgrade`` drops what
``upgrade`` added. SQLite cannot add a constraint to an existing table, so the
foreign key is created only on other dialects (tests run on SQLite).

Idempotent (AE-0371 review): prod has no ``alembic_version`` table and the SQL
was applied by hand, so every column and the foreign key is added only when
missing and dropped only when present. A later ``alembic upgrade`` on prod is a
no-op for this revision.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b0c1d2e3f4a5"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None

_PROJECTS = "carousel_projects"
_ASSETS = "carousel_creator_assets"
_FK_HOOK_ASSET = "fk_carousel_projects_hook_asset"
_SQLITE = "sqlite"

_PROJECT_COLUMNS: tuple[tuple[str, sa.types.TypeEngine[object]], ...] = (
    ("content_mode", sa.String(20)),
    ("pov_thesis", sa.String(280)),
    ("pov_personal_proof", sa.String(500)),
    ("pov_format", sa.String(30)),
    ("slide_count", sa.Integer()),
    ("cta_goal", sa.String(20)),
    ("hook_text", sa.String(120)),
    ("hook_asset_id", sa.String(36)),
)
_ASSET_COLUMNS: tuple[tuple[str, sa.types.TypeEngine[object]], ...] = (
    ("role", sa.String(16)),
    ("pose_tag", sa.String(40)),
)


def _supports_alter_constraints() -> bool:
    return op.get_bind().dialect.name != _SQLITE


def _existing_columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _has_hook_asset_fk() -> bool:
    foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys(_PROJECTS)
    return any(fk.get("name") == _FK_HOOK_ASSET for fk in foreign_keys)


def _add_missing(
    table: str, columns: tuple[tuple[str, sa.types.TypeEngine[object]], ...]
) -> None:
    present = _existing_columns(table)
    for name, column_type in columns:
        if name in present:
            continue
        op.add_column(table, sa.Column(name, column_type, nullable=True))


def _drop_present(
    table: str, columns: tuple[tuple[str, sa.types.TypeEngine[object]], ...]
) -> None:
    present = _existing_columns(table)
    for name, _column_type in reversed(columns):
        if name not in present:
            continue
        op.drop_column(table, name)


def upgrade() -> None:
    """Add the nullable content-mode and creator-asset columns (if missing)."""
    _add_missing(_PROJECTS, _PROJECT_COLUMNS)
    _add_missing(_ASSETS, _ASSET_COLUMNS)
    if _supports_alter_constraints() and not _has_hook_asset_fk():
        op.create_foreign_key(
            _FK_HOOK_ASSET,
            _PROJECTS,
            _ASSETS,
            ["hook_asset_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Drop the columns added by ``upgrade`` (only those present)."""
    if _supports_alter_constraints() and _has_hook_asset_fk():
        op.drop_constraint(_FK_HOOK_ASSET, _PROJECTS, type_="foreignkey")
    _drop_present(_ASSETS, _ASSET_COLUMNS)
    _drop_present(_PROJECTS, _PROJECT_COLUMNS)
