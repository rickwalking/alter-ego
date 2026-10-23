"""The carousel rubric ACL, the content-phase scoring step and the scoped average.

Feature: backend/tests/features/carousel_rubric_ae0504.feature
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from rag_backend.application.services.carousel.carousel_rubric_step import (
    CarouselRubricStep,
    RubricScoreInput,
    slides_text,
)
from rag_backend.domain.carousel_rubric_scoring import build_rubric_evaluation
from rag_backend.domain.models import CarouselProject, CarouselTheme
from rag_backend.domain.models.carousel_rubric import (
    CarouselRubric,
    CarouselRubricEvaluation,
    JudgedCriterion,
    RubricJudgeRequest,
)
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.persona_rubric import (
    QualityRubricModel,
    RubricEvaluationScoreModel,
)
from rag_backend.modules.editorial.public import CarouselRubricAcl, RubricChoiceError
from rag_backend.modules.publishing import AnalyticsQuery
from rag_backend.modules.publishing.infrastructure.publishing_read_acl import (
    PublishingReadAcl,
)

CRITERION = {
    "id": "clarity",
    "name": "Clareza",
    "description": "Uma ideia por slide",
    "weight": 1.0,
    "evaluation_method": "ai_auto",
    "min_threshold": 0.7,
    "scoring_scale": "0-100",
    "prompt_template": "Avalie {content}",
}
DRAFTS = [
    {"slide_index": 1, "draft_text": "Gancho forte"},
    {"slide_index": 2, "draft_text": ""},
    "not a slide",
    {"draft_text": "Fecho"},
]


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


async def _rubric(
    session: AsyncSession,
    name: str,
    *,
    default: bool = False,
    types: list[str] | None = None,
    age: int = 0,
) -> str:
    model = QualityRubricModel(
        name=name,
        criteria=[CRITERION],
        applicable_content_types=types or ["carousel"],
        is_default=default,
        created_at=datetime.now(UTC) - timedelta(days=age),
    )
    session.add(model)
    await session.commit()
    return str(model.id)


async def _carousel(
    session: AsyncSession, rubric_id: str | None, owner: str = "owner-1"
) -> str:
    project = CarouselProject(
        topic=f"Topic {owner}",
        audience="Devs",
        niche="IA",
        theme=CarouselTheme.AI_COMPETITION,
        owner_id=owner,
        rubric_id=rubric_id,
    )
    created = await PostgresCarouselRepository(session).create_project(project)
    await session.commit()
    return str(created.id)


class _Judge:
    """Answers a fixed score, or fails like a judge that never parses."""

    def __init__(
        self, score: float | None, failure: type[Exception] = ValueError
    ) -> None:
        self.score_value = score
        self.failure = failure
        self.requests: list[RubricJudgeRequest] = []

    async def score(self, request: RubricJudgeRequest) -> CarouselRubricEvaluation:
        self.requests.append(request)
        if self.score_value is None:
            raise self.failure("invalid_json")
        return build_rubric_evaluation(
            request.rubric, [JudgedCriterion("clarity", self.score_value)], "ok"
        )


def _state(update: dict[str, object]) -> dict[str, object]:
    scores = update["rubric_scores"]
    assert isinstance(scores, dict)
    return scores


async def _score_rows(session: AsyncSession, project_id: str) -> list[int]:
    rows = await session.execute(
        select(RubricEvaluationScoreModel.overall_score).where(
            RubricEvaluationScoreModel.content_id == project_id
        )
    )
    return [int(value) for value in rows.scalars()]


async def test_create_takes_the_oldest_default_carousel_rubric(
    db_session: AsyncSession,
) -> None:
    """Scenario: A carousel created without a rubric gets the default carousel rubric."""
    acl = CarouselRubricAcl(db_session)
    assert await acl.rubric_for_create(None) is None
    await _rubric(db_session, "Blog default", default=True, types=["blog_post"], age=9)
    newer = await _rubric(db_session, "Newer default", default=True, age=1)
    older = await _rubric(db_session, "Older default", default=True, age=5)

    assert await acl.rubric_for_create(None) == older
    assert await acl.rubric_for_create(newer) == newer


async def test_create_refuses_unknown_and_non_carousel_rubrics(
    db_session: AsyncSession,
) -> None:
    """Scenario: A rubric that cannot be used is refused at create."""
    acl = CarouselRubricAcl(db_session)
    blog_only = await _rubric(db_session, "Blog", types=["blog_post"])

    with pytest.raises(RubricChoiceError, match="rubric_not_found"):
        await acl.rubric_for_create("00000000-0000-0000-0000-00000000dead")
    with pytest.raises(RubricChoiceError, match="rubric_not_for_carousels"):
        await acl.rubric_for_create(blog_only)


async def test_project_rubric_and_carousels_using(db_session: AsyncSession) -> None:
    """Scenario: A rubric used by a carousel cannot be deleted."""
    rubric_id = await _rubric(db_session, "QA")
    with_rubric = await _carousel(db_session, rubric_id)
    without = await _carousel(db_session, None)
    acl = CarouselRubricAcl(db_session)

    rubric = await acl.project_rubric(with_rubric)
    assert rubric is not None
    assert (rubric.id, rubric.name) == (rubric_id, "QA")
    assert [c["id"] for c in rubric.criteria] == ["clarity"]
    assert await acl.project_rubric(without) is None
    assert await acl.carousels_using(rubric_id) == [(with_rubric, "Topic owner-1")]


async def test_scoring_stores_and_replaces_the_carousel_row(
    db_session: AsyncSession,
) -> None:
    """Scenario: A regeneration replaces the scores, an unchanged draft keeps them."""
    rubric_id = await _rubric(db_session, "QA")
    project_id = await _carousel(db_session, rubric_id)
    step = CarouselRubricStep(db=db_session, judge=_Judge(85))
    rubric = await step.project_rubric(project_id)

    first = await step.score(
        RubricScoreInput(
            project_id=project_id,
            rubric=rubric,
            slide_drafts=DRAFTS,
            regenerated=True,
            has_scores=False,
        )
    )
    second = await CarouselRubricStep(db=db_session, judge=_Judge(40)).score(
        RubricScoreInput(
            project_id=project_id,
            rubric=rubric,
            slide_drafts=DRAFTS,
            regenerated=True,
            has_scores=True,
        )
    )

    assert _state(first)["overall_score"] == 85
    assert _state(second)["passed"] is False
    assert await _score_rows(db_session, project_id) == [40]


async def test_scoring_is_skipped_when_nothing_to_score(
    db_session: AsyncSession,
) -> None:
    """Scenario: A regeneration replaces the scores, an unchanged draft keeps them."""
    rubric = CarouselRubric(id="r", name="R", criteria=())
    judge = _Judge(90)
    step = CarouselRubricStep(db=db_session, judge=judge)

    assert (
        await step.score(
            RubricScoreInput(
                project_id="p",
                rubric=None,
                slide_drafts=DRAFTS,
                regenerated=True,
                has_scores=False,
            )
        )
        == {}
    )
    assert (
        await step.score(
            RubricScoreInput(
                project_id="p",
                rubric=rubric,
                slide_drafts=DRAFTS,
                regenerated=False,
                has_scores=True,
            )
        )
        == {}
    )
    assert (
        await step.score(
            RubricScoreInput(
                project_id="p",
                rubric=rubric,
                slide_drafts=[],
                regenerated=True,
                has_scores=False,
            )
        )
        == {}
    )
    assert (
        await CarouselRubricStep(db=db_session, judge=None).score(
            RubricScoreInput(
                project_id="p",
                rubric=rubric,
                slide_drafts=DRAFTS,
                regenerated=True,
                has_scores=False,
            )
        )
        == {}
    )
    assert await CarouselRubricStep(db=None, judge=judge).project_rubric("p") is None
    assert await step.project_rubric("") is None
    assert judge.requests == []


async def test_a_judge_failure_leaves_no_scores(db_session: AsyncSession) -> None:
    """Scenario: A judge failure leaves the run going without scores."""
    rubric_id = await _rubric(db_session, "QA")
    project_id = await _carousel(db_session, rubric_id)
    step = CarouselRubricStep(db=db_session, judge=_Judge(None))
    rubric = await step.project_rubric(project_id)

    assert (
        await step.score(
            RubricScoreInput(
                project_id=project_id,
                rubric=rubric,
                slide_drafts=DRAFTS,
                regenerated=True,
                has_scores=False,
            )
        )
        == {}
    )
    assert await _score_rows(db_session, project_id) == []


def test_the_judge_reads_the_slides_in_order() -> None:
    """Scenario: The drafted carousel is scored on 0-100 per criterion."""
    assert slides_text(DRAFTS) == "Slide 1: Gancho forte\n\nSlide 4: Fecho"
    assert slides_text("nope") == ""


async def test_the_quality_average_counts_only_own_content(
    db_session: AsyncSession,
) -> None:
    """Scenario: The quality average counts only the caller's own content."""
    rubric_id = await _rubric(db_session, "QA")
    mine = await _carousel(db_session, rubric_id, owner="editor-1")
    theirs = await _carousel(db_session, rubric_id, owner="editor-2")
    rubric = await CarouselRubricAcl(db_session).project_rubric(mine)
    assert rubric is not None
    for project_id, score in ((mine, 90), (theirs, 50)):
        await CarouselRubricAcl(db_session).replace_scores(
            project_id,
            build_rubric_evaluation(rubric, [JudgedCriterion("clarity", score)]),
        )
    acl = PublishingReadAcl(db_session)

    own = await acl.project_analytics(AnalyticsQuery(author_id="editor-1"))
    everyone = await acl.project_analytics(AnalyticsQuery(author_id=None))

    assert (own.summary.quality_score_average, own.summary.quality_score_count) == (
        90.0,
        1,
    )
    assert everyone.summary.quality_score_count == 2
    assert everyone.summary.quality_score_average == 70.0


async def test_a_wrong_shape_answer_also_leaves_no_scores(
    db_session: AsyncSession,
) -> None:
    """Scenario: A judge failure leaves the run going without scores."""
    rubric_id = await _rubric(db_session, "QA")
    project_id = await _carousel(db_session, rubric_id)
    step = CarouselRubricStep(db=db_session, judge=_Judge(None, TypeError))
    rubric = await step.project_rubric(project_id)

    update = await step.score(
        RubricScoreInput(
            project_id=project_id,
            rubric=rubric,
            slide_drafts=DRAFTS,
            regenerated=True,
            has_scores=False,
        )
    )

    assert update == {}
    assert await _score_rows(db_session, project_id) == []


async def test_a_failed_re_score_drops_the_stale_scores(
    db_session: AsyncSession,
) -> None:
    """Scenario: A failed re-score of regenerated drafts drops the old scores."""
    rubric_id = await _rubric(db_session, "QA")
    project_id = await _carousel(db_session, rubric_id)
    rubric = await CarouselRubricStep(db=db_session, judge=None).project_rubric(
        project_id
    )
    await CarouselRubricStep(db=db_session, judge=_Judge(85)).score(
        RubricScoreInput(
            project_id=project_id,
            rubric=rubric,
            slide_drafts=DRAFTS,
            regenerated=True,
            has_scores=False,
        )
    )

    update = await CarouselRubricStep(db=db_session, judge=_Judge(None)).score(
        RubricScoreInput(
            project_id=project_id,
            rubric=rubric,
            slide_drafts=DRAFTS,
            regenerated=True,
            has_scores=True,
        )
    )

    assert update == {"rubric_scores": {}}
    assert await _score_rows(db_session, project_id) == []


async def test_a_post_authors_own_scores_count_and_nothing_reads_as_no_data(
    db_session: AsyncSession,
) -> None:
    """Scenario: The quality average counts only the caller's own content."""
    from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

    rubric_id = await _rubric(db_session, "QA")
    post = BlogPostModel.from_entity({
        "title": "Post",
        "slug": "post-own",
        "status": "draft",
        "content": {},
        "author_id": "writer-1",
    })
    db_session.add(post)
    await db_session.flush()
    db_session.add(
        RubricEvaluationScoreModel(
            rubric_id=rubric_id,
            content_id=str(post.id),
            content_type="blog_post",
            scores={},
            overall_score=72,
            passed=True,
            feedback=[],
        )
    )
    await db_session.commit()
    acl = PublishingReadAcl(db_session)

    writer = await acl.project_analytics(AnalyticsQuery(author_id="writer-1"))
    nobody = await acl.project_analytics(AnalyticsQuery(author_id="nobody"))

    assert (
        writer.summary.quality_score_average,
        writer.summary.quality_score_count,
    ) == (
        72.0,
        1,
    )
    assert (
        nobody.summary.quality_score_average,
        nobody.summary.quality_score_count,
    ) == (
        None,
        0,
    )
