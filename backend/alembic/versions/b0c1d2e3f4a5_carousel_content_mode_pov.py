"""carousel content mode and pov inputs; creator asset role and pose

Revision ID: b0c1d2e3f4a5
Revises: f8a9b0c1d2e3
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
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "b0c1d2e3f4a5"
down_revision = "f8a9b0c1d2e3"
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


def upgrade() -> None:
    """Add the nullable content-mode and creator-asset columns."""
    for name, column_type in _PROJECT_COLUMNS:
        op.add_column(_PROJECTS, sa.Column(name, column_type, nullable=True))
    for name, column_type in _ASSET_COLUMNS:
        op.add_column(_ASSETS, sa.Column(name, column_type, nullable=True))
    if _supports_alter_constraints():
        op.create_foreign_key(
            _FK_HOOK_ASSET,
            _PROJECTS,
            _ASSETS,
            ["hook_asset_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Drop the columns added by ``upgrade``."""
    if _supports_alter_constraints():
        op.drop_constraint(_FK_HOOK_ASSET, _PROJECTS, type_="foreignkey")
    for name, _column_type in reversed(_ASSET_COLUMNS):
        op.drop_column(_ASSETS, name)
    for name, _column_type in reversed(_PROJECT_COLUMNS):
        op.drop_column(_PROJECTS, name)
