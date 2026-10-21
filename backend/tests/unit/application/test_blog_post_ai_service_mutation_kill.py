"""Assertion-bearing tests that pin exact BlogPostAIService behaviour.

Feature: Blog post AI suggestions, improvements and section rewrites
"""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.sql import Select

from rag_backend.application.services.blog_post_ai_service import (
    BlogAiTraceContext,
    BlogPostAIService,
    _ImproveInput,
    _RewriteInput,
    _SuggestInput,
)
from rag_backend.domain.constants.blog_document import BLOG_SECTION_MAX_CHARS
from rag_backend.domain.constants.blog_editor import (
    PHASE_BLOG_SECTION_REWRITE,
    REWRITE_NO_HEADING_INSTRUCTION,
)
from rag_backend.domain.constants.input_sanitizer import MAX_LLM_INPUT_LENGTH

MODULE = "rag_backend.application.services.blog_post_ai_service"
UNKNOWN_POST = "unknown"
POST_ID = "post-9"
ACTION = "improve"


@pytest.fixture
def propagate() -> Iterator[MagicMock]:
    """Patch the trace helpers and expose the propagate mock."""
    context = MagicMock(__enter__=MagicMock(), __exit__=MagicMock(return_value=False))
    with (
        patch(f"{MODULE}.start_blog_workflow_trace", return_value=None),
        patch(f"{MODULE}.blog_ai_propagate", return_value=context) as mock,
    ):
        yield mock


@pytest.fixture
def chat_model() -> MagicMock:
    """A sentinel chat model."""
    return MagicMock(name="chat_model")


@pytest.fixture
def service(chat_model: MagicMock) -> BlogPostAIService:
    """A service whose LLM returns an empty answer by default."""
    llm = MagicMock()
    llm.generate = AsyncMock(return_value="")
    llm.chat_model = chat_model
    return BlogPostAIService(llm_service=llm)


@pytest.fixture
def persona() -> MagicMock:
    """A sentinel persona entity."""
    return MagicMock(name="persona_entity")


@pytest.fixture
def db(persona: MagicMock) -> MagicMock:
    """A DB whose default-persona query returns the sentinel persona."""
    model = MagicMock()
    model.to_entity = MagicMock(return_value=persona)
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=model)
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.get = AsyncMock(return_value=None)
    return session


@pytest.fixture
def agent_cls() -> Iterator[MagicMock]:
    """Patch PersonaAgent; enforce echoes a fixed body by default."""
    with patch(f"{MODULE}.PersonaAgent") as mock:
        mock.return_value.enforce = AsyncMock(return_value="Body")
        yield mock


# Scenario: Suggest without a trace propagates the unknown post id
async def test_suggest_without_trace_propagates_unknown(
    service: BlogPostAIService, propagate: MagicMock
) -> None:
    """No trace context propagates the literal unknown post id."""
    await service.suggest(_SuggestInput("text", action=ACTION))

    propagate.assert_called_once_with(UNKNOWN_POST, "ai_suggest")


# Scenario: An empty model answer becomes an empty suggestion
async def test_suggest_empty_answer_is_empty_text(
    service: BlogPostAIService, propagate: MagicMock
) -> None:
    """An empty LLM answer yields an empty suggested text."""
    result = await service.suggest(_SuggestInput("text", action=ACTION))

    assert result["suggested_text"] == ""


# Scenario: Improve without a trace propagates the unknown post id
async def test_improve_without_trace_propagates_unknown(
    service: BlogPostAIService, propagate: MagicMock, db: MagicMock
) -> None:
    """No trace context on improve propagates the literal unknown post id."""
    await service.improve(_ImproveInput(db=db, text="text", action=ACTION))

    propagate.assert_called_once_with(UNKNOWN_POST, "ai_improve")


# Scenario: Rewrite without a trace propagates the unknown post id
async def test_rewrite_without_trace_propagates_unknown(
    service: BlogPostAIService,
    propagate: MagicMock,
    db: MagicMock,
    agent_cls: MagicMock,
) -> None:
    """No trace context on rewrite propagates unknown and the rewrite phase."""
    await service.rewrite_section(_RewriteInput(db=db, body_md="body"))

    propagate.assert_called_once_with(UNKNOWN_POST, PHASE_BLOG_SECTION_REWRITE)


# Scenario: Rewrite with a trace propagates the given post id
async def test_rewrite_with_trace_propagates_post_id(
    service: BlogPostAIService,
    propagate: MagicMock,
    db: MagicMock,
    agent_cls: MagicMock,
) -> None:
    """A trace context post id is propagated unchanged."""
    trace = BlogAiTraceContext(post_id=POST_ID)

    await service.rewrite_section(_RewriteInput(db=db, body_md="body", trace=trace))

    propagate.assert_called_once_with(POST_ID, PHASE_BLOG_SECTION_REWRITE)


# Scenario: Rewrite enforces the persona voice with the heading context
async def test_rewrite_builds_agent_and_enforce_call(
    service: BlogPostAIService,
    propagate: MagicMock,
    db: MagicMock,
    agent_cls: MagicMock,
    persona: MagicMock,
    chat_model: MagicMock,
) -> None:
    """The persona agent gets the persona and chat model; enforce gets context."""
    await service.rewrite_section(
        _RewriteInput(db=db, body_md="the body", heading="Title")
    )

    agent_cls.assert_called_once_with(persona=persona, llm=chat_model)
    agent_cls.return_value.enforce.assert_awaited_once_with(
        "the body", context=f"Title\n\n{REWRITE_NO_HEADING_INSTRUCTION}"
    )


# Scenario: Rewrite drops a heading echoed back by the model
async def test_rewrite_strips_heading_echo(
    service: BlogPostAIService,
    propagate: MagicMock,
    db: MagicMock,
    agent_cls: MagicMock,
) -> None:
    """A leading bold echo of the heading is removed from the rewrite."""
    agent_cls.return_value.enforce.return_value = "**Title**\n\nReal body"

    text = await service.rewrite_section(
        _RewriteInput(db=db, body_md="body", heading="Title")
    )

    assert text == "Real body"


# Scenario: Rewrite falls back to the oldest persona
async def test_rewrite_default_persona_query(
    service: BlogPostAIService,
    propagate: MagicMock,
    db: MagicMock,
    agent_cls: MagicMock,
) -> None:
    """The default persona is the oldest persona profile, limited to one row."""
    await service.rewrite_section(_RewriteInput(db=db, body_md="body"))

    statement = db.execute.await_args[0][0]
    assert isinstance(statement, Select)
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "FROM persona_profiles" in sql
    assert "ORDER BY persona_profiles.created_at" in sql
    assert sql.rstrip().endswith("LIMIT 1")


# Scenario: A body exactly at the LLM input limit is accepted
async def test_rewrite_accepts_body_at_input_limit(
    service: BlogPostAIService,
    propagate: MagicMock,
    db: MagicMock,
    agent_cls: MagicMock,
) -> None:
    """A body of exactly MAX_LLM_INPUT_LENGTH characters is rewritten."""
    body = "x" * MAX_LLM_INPUT_LENGTH

    assert await service.rewrite_section(_RewriteInput(db=db, body_md=body)) == "Body"


# Scenario: A rewrite exactly at the section limit is accepted
async def test_rewrite_accepts_output_at_section_limit(
    service: BlogPostAIService,
    propagate: MagicMock,
    db: MagicMock,
    agent_cls: MagicMock,
) -> None:
    """A rewrite of exactly BLOG_SECTION_MAX_CHARS characters is returned."""
    output = "y" * BLOG_SECTION_MAX_CHARS
    agent_cls.return_value.enforce.return_value = output

    assert await service.rewrite_section(_RewriteInput(db=db, body_md="b")) == output


# Scenario: Heading echo match only strips hash markers
async def test_rewrite_keeps_line_that_differs_by_leading_x(
    service: BlogPostAIService,
    propagate: MagicMock,
    db: MagicMock,
    agent_cls: MagicMock,
) -> None:
    """A first line equal to the heading minus a leading X is not an echo."""
    agent_cls.return_value.enforce.return_value = "ray\nBody"

    text = await service.rewrite_section(
        _RewriteInput(db=db, body_md="b", heading="Xray")
    )

    assert text == "ray\nBody"


# Scenario: Heading echo match collapses whitespace runs
async def test_rewrite_strips_echo_with_different_whitespace(
    service: BlogPostAIService,
    propagate: MagicMock,
    db: MagicMock,
    agent_cls: MagicMock,
) -> None:
    """An echo whose inner whitespace differs from the heading is still removed."""
    agent_cls.return_value.enforce.return_value = "# My   Title\nBody"

    text = await service.rewrite_section(
        _RewriteInput(db=db, body_md="b", heading="My Title")
    )

    assert text == "Body"
