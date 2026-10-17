"""AE-0416: PT blog body without the English research intro; Rejected board column.

Scenarios: see tests/features/qa_followups_ae0416.feature.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from rag_backend.application.services.carousel.blog_composition import (
    BlogCompositionInput,
    build_blog_markdown_en_from_long_form_notes,
    build_blog_markdown_from_long_form_notes,
)
from rag_backend.application.services.carousel.editorial_distribution_constants import (
    LONG_FORM_NOTES_KEY,
    OUTLINE_LEGACY_HEADING_KEY,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_CONTENT,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_REJECTED,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.publishing import (
    BOARD_PHASES,
    BoardProjection,
    BoardQuery,
    PublishingReadAcl,
)
from rag_backend.modules.publishing.constants import BOARD_COLUMN_REJECTED

_RESEARCH = "Researchers found that the model leaked."


def _composition(research: str = _RESEARCH) -> BlogCompositionInput:
    return BlogCompositionInput(
        slides=(
            {"slide_index": 1, "title": "Gancho", LONG_FORM_NOTES_KEY: "Notas PT."},
        ),
        title="Título",
        research_summary=research,
        outline=({"slide_index": 1, "title": "Gancho"},),
    )


_TRANSLATIONS: dict[int, dict[str, object]] = {
    1: {OUTLINE_LEGACY_HEADING_KEY: "Hook", LONG_FORM_NOTES_KEY: "EN notes."},
}


@pytest.mark.unit
class TestBlogBodyLanguage:
    """The PT body is Portuguese from its first line; EN keeps the research."""

    def test_pt_body_has_no_english_research_intro(self) -> None:
        # Scenario: The PT blog body never carries the English research intro
        markdown = build_blog_markdown_from_long_form_notes(_composition())
        assert markdown == "# Título\n\n## Gancho\n\nNotas PT."
        assert _RESEARCH not in markdown

    def test_en_body_keeps_research_intro(self) -> None:
        # Scenario: The EN blog body keeps the research intro
        markdown = build_blog_markdown_en_from_long_form_notes(
            _composition(), _TRANSLATIONS
        )
        assert markdown == f"# Título\n\n{_RESEARCH}\n\n## Hook\n\nEN notes."

    def test_en_body_without_research_starts_with_section(self) -> None:
        # Scenario: An empty research summary leaves the EN body without an intro
        markdown = build_blog_markdown_en_from_long_form_notes(
            _composition("  "), _TRANSLATIONS
        )
        assert markdown == "# Título\n\n## Hook\n\nEN notes."


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """SQLite in-memory session with the ORM schema created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _board_with(
    session: AsyncSession, project: tuple[str, str]
) -> BoardProjection:
    phase, phase_status = project
    session.add(
        CarouselProjectModel(
            id=str(uuid4()),
            topic=f"{phase}-{phase_status}",
            audience="aud",
            niche="N",
            theme="ai_competition",
            current_phase=phase,
            phase_status=phase_status,
        )
    )
    await session.commit()
    return await PublishingReadAcl(session).project_board(BoardQuery())


def _topics(projection: BoardProjection, column: str) -> list[str]:
    cards = next(col.cards for col in projection.columns if col.phase == column)
    return [card.topic for card in cards]


@pytest.mark.unit
@pytest.mark.asyncio
class TestRejectedBoardColumn:
    """Rejected projects leave the phase columns for their own column."""

    async def test_rejected_brief_project_is_in_rejected_column(
        self, db_session: AsyncSession
    ) -> None:
        # Scenario: A rejected project goes to the Rejected column
        board = await _board_with(db_session, (PHASE_BRIEF, PHASE_STATUS_REJECTED))
        assert _topics(board, BOARD_COLUMN_REJECTED) == ["brief-rejected"]
        assert _topics(board, PHASE_BRIEF) == []

    async def test_rejected_card_keeps_its_phase(
        self, db_session: AsyncSession
    ) -> None:
        # Scenario: A project rejected at a later phase keeps that phase on its card
        board = await _board_with(db_session, (PHASE_CONTENT, PHASE_STATUS_REJECTED))
        rejected = next(c for c in board.columns if c.phase == BOARD_COLUMN_REJECTED)
        assert [card.current_phase for card in rejected.cards] == [PHASE_CONTENT]
        assert rejected.cards[0].phase_status == PHASE_STATUS_REJECTED
        assert _topics(board, PHASE_CONTENT) == []

    async def test_rejected_column_is_last(self, db_session: AsyncSession) -> None:
        # Scenario: The Rejected column is the last column
        board = await PublishingReadAcl(db_session).project_board(BoardQuery())
        assert [col.phase for col in board.columns] == [
            *BOARD_PHASES,
            BOARD_COLUMN_REJECTED,
        ]

    async def test_active_project_stays_in_phase_column(
        self, db_session: AsyncSession
    ) -> None:
        # Scenario: Non-rejected projects stay in their phase column
        board = await _board_with(
            db_session, (PHASE_CONTENT, PHASE_STATUS_AWAITING_HUMAN)
        )
        assert _topics(board, PHASE_CONTENT) == ["content-awaiting_human"]
        assert _topics(board, BOARD_COLUMN_REJECTED) == []
