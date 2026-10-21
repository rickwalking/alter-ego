"""Load what the owner autofix reads for one carousel.

The persisted slide rows are the source of truth (what the renderer reads):
they become canonical localized-slide records. The workflow checkpoint gives
the outline (key points per slide) and the research titles; together with the
copy itself they form the carousel's proper-noun vocabulary.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rag_backend.application.services.carousel.carousel_repair_projection import (
    localized_from_slides,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.owner_autofix_paths import (
    text_at,
    visible_paths,
)
from rag_backend.application.services.carousel.owner_autofix_plan import (
    AutofixContext,
    SlideOutline,
)
from rag_backend.application.services.carousel.owner_autofix_vocabulary import (
    VocabularySources,
    build_vocabulary,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.structure_fill import (
    outline_from_state,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_LOCALIZED_SLIDES,
    STATE_FIELD_PRESENTATION_POLICY_VERSION,
    STATE_FIELD_RESEARCH_FINDINGS,
)
from rag_backend.domain.protocols.repositories import CarouselRepository

_TITLE = "title"
_KEY_POINTS = "key_points"
_SUMMARY = "summary"


class WorkflowStateStore(Protocol):
    """Checkpoint read/patch. ``EditorialWorkflowService`` satisfies it."""

    async def get_workflow_state(self, project_id: str) -> Mapping[str, object] | None:
        """The checkpoint state, or None when there is none."""
        ...

    async def update_workflow_state(
        self, project_id: str, values: dict[str, object]
    ) -> None:
        """Patch the checkpoint without advancing the workflow."""
        ...


@dataclass(frozen=True)
class AutofixSourceRequest:
    """Where to read one carousel from."""

    repo: CarouselRepository
    project_id: str
    workflow: WorkflowStateStore | None = None


@dataclass(frozen=True)
class AutofixSource:
    """Records from the rows, the plan context, and the checkpoint state."""

    policy_version: str
    records: list[dict[str, object]]
    context: AutofixContext
    state: Mapping[str, object] | None


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        item.strip() for item in value if isinstance(item, str) and item.strip()
    )


def _dicts(state: Mapping[str, object] | None, key: str) -> list[Mapping[str, object]]:
    raw = state.get(key) if state is not None else None
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _record_texts(records: list[dict[str, object]]) -> tuple[str, ...]:
    texts: list[str] = []
    for record in records:
        for key in (PRESENTATION_PT_KEY, PRESENTATION_EN_KEY):
            payload = as_dict(record.get(key)) or {}
            texts.extend(text_at(payload, path) for path in visible_paths(payload))
    return tuple(text for text in texts if text)


def _research(
    state: Mapping[str, object] | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(titles, sentence-case texts) of the research findings."""
    findings = _dicts(state, STATE_FIELD_RESEARCH_FINDINGS)
    titles = tuple(str(item.get(_TITLE) or "") for item in findings)
    texts: list[str] = [str(item.get(_SUMMARY) or "") for item in findings]
    for item in findings:
        texts.extend(_strings(item.get(_KEY_POINTS)))
    return titles, tuple(texts)


@dataclass(frozen=True)
class _VocabularyInput:
    state: Mapping[str, object] | None
    outline: Mapping[int, SlideOutline]
    records: list[dict[str, object]]
    topic: str
    configured: tuple[str, ...]


def _vocabulary(source: _VocabularyInput) -> tuple[str, ...]:
    titles, research_texts = _research(source.state)
    outline_texts = [
        text
        for entry in source.outline.values()
        for text in (entry.title, *entry.key_points)
    ]
    return build_vocabulary(
        VocabularySources(
            trusted=(*outline_texts, *research_texts),
            copy=_record_texts(source.records),
            titles=(source.topic, *titles),
            configured=source.configured,
        )
    )


@dataclass(frozen=True)
class _SourceParts:
    state: Mapping[str, object] | None
    records: list[dict[str, object]]
    topic: str
    version: str


def _source(parts: _SourceParts) -> AutofixSource:
    policy = load_presentation_policy(parts.version)
    state = parts.state
    records = parts.records
    outline = outline_from_state(state)
    vocabulary = _vocabulary(
        _VocabularyInput(
            state=state,
            outline=outline,
            records=records,
            topic=parts.topic,
            configured=policy.proper_nouns,
        )
    )
    context = AutofixContext(policy=policy, vocabulary=vocabulary, outline=outline)
    return AutofixSource(
        policy_version=parts.version, records=records, context=context, state=state
    )


async def load_autofix_source(request: AutofixSourceRequest) -> AutofixSource | None:
    """Read rows + checkpoint; None when the carousel does not exist."""
    project = await request.repo.get_project_by_id(UUID(request.project_id))
    if project is None:
        return None
    rows = await request.repo.get_slides_by_project(project.id)
    state = None
    if request.workflow is not None:
        state = await request.workflow.get_workflow_state(request.project_id)
    version = project.presentation_policy_version or DEFAULT_PRESENTATION_POLICY_VERSION
    return _source(
        _SourceParts(
            state=state,
            records=localized_from_slides(rows),
            topic=project.topic,
            version=version,
        )
    )


def _checkpoint_records(state: Mapping[str, object]) -> list[dict[str, object]]:
    raw = state.get(STATE_FIELD_LOCALIZED_SLIDES)
    if not isinstance(raw, list):
        return []
    return [dict(slide) for slide in raw if isinstance(slide, Mapping)]


def _checkpoint_version(state: Mapping[str, object], fallback: str) -> str:
    version = state.get(STATE_FIELD_PRESENTATION_POLICY_VERSION)
    if isinstance(version, str) and version:
        return version
    return fallback


async def load_gate_source(request: AutofixSourceRequest) -> AutofixSource | None:
    """The checkpoint copy at a review gate; None when there is none.

    Before finalize the rows are not the copy the engine validates: the
    checkpoint's ``localized_slides`` are. The plan context is built the same
    way as for the rows.
    """
    if request.workflow is None:
        return None
    project = await request.repo.get_project_by_id(UUID(request.project_id))
    if project is None:
        return None
    state = await request.workflow.get_workflow_state(request.project_id)
    records = _checkpoint_records(state) if state is not None else []
    if state is None or not records:
        return None
    fallback = (
        project.presentation_policy_version or DEFAULT_PRESENTATION_POLICY_VERSION
    )
    return _source(
        _SourceParts(
            state=state,
            records=records,
            topic=project.topic,
            version=_checkpoint_version(state, fallback),
        )
    )


__all__ = [
    "AutofixSource",
    "AutofixSourceRequest",
    "WorkflowStateStore",
    "load_autofix_source",
    "load_gate_source",
]
