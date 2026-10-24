"""The cover generation table's Alembic revision chains on the archived_at one.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature).
"""

from __future__ import annotations

from tests.integration.test_autopilot_migration import ALEMBIC_HEAD, _alembic_config

_REVISION = "344dec4495d3"
_PARENT = "aa4a5695681f"


def test_revision_is_the_single_head_on_top_of_archived_at() -> None:
    """Scenario: Every call is logged for the budget."""
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    assert list(script.get_heads()) == [ALEMBIC_HEAD] == [_REVISION]
    revision = script.get_revision(_REVISION)
    assert revision is not None
    assert revision.down_revision == _PARENT
