"""The copy version store on Postgres: newest text per field, paged reads.

Feature: backend/tests/features/carousel_copy_versions_ae0506.feature
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker

from rag_backend.domain.models.carousel_copy_version import (
    NewCopyVersion,
    VersionPage,
)
from rag_backend.infrastructure.database.copy_version_repository import (
    PostgresCopyVersionStore,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_PROJECT = "carousel-pg"


def _version(field: str, text: str) -> NewCopyVersion:
    return NewCopyVersion(field=field, text=text, author_id=None, summary="edit")


@requires_postgres
async def test_newest_text_per_field_and_pages() -> None:
    """Scenario: The history is read a page at a time."""
    async with isolated_schema(["users", "content_versions"]) as engine:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            store = PostgresCopyVersionStore(session)
            await store.add(
                _PROJECT,
                [
                    _version("caption", "c1"),
                    _version("linkedin_post_pt", "p1"),
                    _version("caption", "c2"),
                ],
            )
            await store.add("other", [_version("caption", "elsewhere")])
            await session.commit()
            latest = await store.latest_texts(_PROJECT)
            first = await store.list_versions(_PROJECT, VersionPage(limit=2))
            older = await store.list_versions(
                _PROJECT, VersionPage(limit=2, before=first[-1].version_number)
            )

    assert latest == {"caption": "c2", "linkedin_post_pt": "p1"}
    assert [v.version_number for v in first] == [3, 2]
    assert [(v.version_number, v.text) for v in older] == [(1, "c1")]
