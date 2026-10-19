"""Targeted repair of the fields the content gate blocks (AE-0430).

Prod carousel 5344b6c6 kept 12 blockers through two owner revisions: the
fail-closed chain only re-drafts a whole slide once, without the violations,
and nothing ever asked a model to fix the field that broke a rule.

``run_gate_repair``: validate, fill PT structure EN lacks, send ONLY the failing
fields (path, current text, exact limit, problems, slide heading, PT source)
in one model call, patch the answers in by path, re-validate. At most
``GATE_REPAIR_MAX_ROUNDS`` rounds, then stop with what still blocks visible.
Never truncates, never loosens a rule, never raises: a failing model leaves
the copy as it was.

The LangChain model and its Langfuse runnable config are injected by the
orchestrator (agents layer), so this module adds no application ->
infrastructure import.
"""

from __future__ import annotations

import asyncio
import copy
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from rag_backend.application.services.carousel.content_gate_repair_targets import (
    FieldRepairTarget,
    TargetPlan,
    apply_fixes,
    fill_missing_en_structure,
    plan_targets,
)
from rag_backend.application.services.carousel.draft_blob_text import (
    parse_object_text,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.application.services.carousel_template.prompts import (
    build_gate_field_repair_prompt,
)
from rag_backend.domain.constants.content_gate_repair import (
    GATE_REPAIR_FIELD_LOCALE,
    GATE_REPAIR_FIELD_MAX_CHARS,
    GATE_REPAIR_FIELD_MAX_LINES,
    GATE_REPAIR_FIELD_PATH,
    GATE_REPAIR_FIELD_PROBLEMS,
    GATE_REPAIR_FIELD_PT_TEXT,
    GATE_REPAIR_FIELD_SLIDE,
    GATE_REPAIR_FIELD_SLIDE_HEADING,
    GATE_REPAIR_FIELD_TEXT,
    GATE_REPAIR_JSON_FIXES_KEY,
    GATE_REPAIR_JSON_ID_KEY,
    GATE_REPAIR_JSON_TEXT_KEY,
    GATE_REPAIR_MAX_ROUNDS,
    GATE_REPAIR_TIMEOUT_SECONDS,
    GATE_REPAIR_VAR_FIELDS_JSON,
    GATE_REPAIR_VAR_STYLE_GUIDE,
    LOG_GATE_REPAIR_DONE,
    LOG_GATE_REPAIR_MODEL_FAILED,
    LOG_GATE_REPAIR_ROUND,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_SLIDE_INDEX,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationReport

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class FieldRepairRequest:
    """One round: the failing fields and the author's style guide."""

    targets: tuple[FieldRepairTarget, ...]
    style_guide: str = ""


class GateFieldRepairer(Protocol):
    """Rewrite the requested fields; answers keyed by target id."""

    async def repair(self, request: FieldRepairRequest) -> dict[str, str]:
        """One model call. May raise on transport or parse failure."""
        ...


def _empty_config() -> RunnableConfig:
    return RunnableConfig()


@dataclass(frozen=True)
class LlmGateRepairConfig:
    """The chat model plus the orchestrator-provided tracing config."""

    llm: BaseChatModel
    runnable_config: Callable[[], RunnableConfig] = field(default=_empty_config)


def _field_json(target: FieldRepairTarget) -> dict[str, object]:
    entry: dict[str, object] = {
        GATE_REPAIR_JSON_ID_KEY: target.target_id,
        GATE_REPAIR_FIELD_SLIDE: target.slide_index,
        GATE_REPAIR_FIELD_LOCALE: target.locale,
        GATE_REPAIR_FIELD_PATH: target.field,
        GATE_REPAIR_FIELD_TEXT: target.text,
        GATE_REPAIR_FIELD_PROBLEMS: list(target.problems),
        GATE_REPAIR_FIELD_SLIDE_HEADING: target.slide_heading,
    }
    optional: dict[str, object] = {
        GATE_REPAIR_FIELD_PT_TEXT: target.source_text or None,
        GATE_REPAIR_FIELD_MAX_CHARS: target.max_characters,
        GATE_REPAIR_FIELD_MAX_LINES: target.max_lines,
    }
    entry.update({key: value for key, value in optional.items() if value is not None})
    return entry


def render_field_repair_prompt(request: FieldRepairRequest) -> str:
    """The versioned prompt for one round."""
    fields = [_field_json(target) for target in request.targets]
    return build_gate_field_repair_prompt({
        GATE_REPAIR_VAR_FIELDS_JSON: json.dumps(fields, ensure_ascii=False, indent=2),
        GATE_REPAIR_VAR_STYLE_GUIDE: request.style_guide,
    })


def parse_fixes(answer: str) -> dict[str, str]:
    """``{"fixes": [{"id", "text"}]}`` as id -> text (fence-aware)."""
    parsed = parse_object_text(answer)
    raw = parsed.get(GATE_REPAIR_JSON_FIXES_KEY) if parsed is not None else None
    if not isinstance(raw, list):
        raise TypeError(GATE_REPAIR_JSON_FIXES_KEY)
    fixes: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        target_id = item.get(GATE_REPAIR_JSON_ID_KEY)
        text = item.get(GATE_REPAIR_JSON_TEXT_KEY)
        if isinstance(target_id, str) and isinstance(text, str):
            fixes[target_id] = text.strip()
    return fixes


class LlmGateFieldRepairer:
    """``GateFieldRepairer`` backed by the fast chat model."""

    def __init__(self, config: LlmGateRepairConfig) -> None:
        self._config = config

    async def repair(self, request: FieldRepairRequest) -> dict[str, str]:
        """Render the prompt, call the model once, parse the answer."""
        response = await self._config.llm.ainvoke(
            [HumanMessage(content=render_field_repair_prompt(request))],
            self._config.runnable_config(),
        )
        return parse_fixes(str(response.content))


@dataclass(frozen=True)
class GateRepairCommand:
    """The localized slides to repair and how."""

    slides: list[dict[str, object]]
    repairer: GateFieldRepairer
    policy_version: str | None = None
    style_guide: str = ""
    project_id: str = ""
    max_rounds: int = GATE_REPAIR_MAX_ROUNDS


@dataclass(frozen=True)
class GateRepairOutcome:
    """Where the loop ended: the slides, the asked ids per round, the report."""

    slides: list[dict[str, object]]
    report: SlideValidationReport
    requested: tuple[tuple[str, ...], ...] = ()
    changed_indices: frozenset[int] = frozenset()


def _fill_structure(
    slides: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[int, tuple[str, ...]]]:
    filled_slides: list[dict[str, object]] = []
    filled: dict[int, tuple[str, ...]] = {}
    for slide in slides:
        updated, paths = fill_missing_en_structure(slide)
        index = slide.get(STATE_FIELD_SLIDE_INDEX)
        if paths and isinstance(index, int):
            filled[index] = paths
        filled_slides.append(updated)
    return filled_slides, filled


async def _ask(
    command: GateRepairCommand, targets: tuple[FieldRepairTarget, ...]
) -> dict[str, str] | None:
    try:
        return await asyncio.wait_for(
            command.repairer.repair(FieldRepairRequest(targets, command.style_guide)),
            timeout=GATE_REPAIR_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # any provider/parse failure keeps the current copy
        logger.warning(
            LOG_GATE_REPAIR_MODEL_FAILED,
            project_id=command.project_id,
            error=type(exc).__name__,
        )
        return None


def _visible(slide: Mapping[str, object]) -> str:
    return json.dumps(
        [slide.get(PRESENTATION_PT_KEY), slide.get(PRESENTATION_EN_KEY)],
        sort_keys=True,
        ensure_ascii=False,
    )


def _changed(
    before: list[dict[str, object]], after: list[dict[str, object]]
) -> frozenset[int]:
    original = {slide.get(STATE_FIELD_SLIDE_INDEX): _visible(slide) for slide in before}
    return frozenset(
        index
        for slide in after
        if isinstance(index := slide.get(STATE_FIELD_SLIDE_INDEX), int)
        and original.get(index) != _visible(slide)
    )


def _validate(
    slides: list[dict[str, object]], command: GateRepairCommand
) -> SlideValidationReport:
    return validate_localized_slides(slides, policy_version=command.policy_version)


async def _round(
    slides: list[dict[str, object]], command: GateRepairCommand
) -> tuple[list[dict[str, object]], tuple[str, ...]] | None:
    """One round; None when there is nothing (more) to ask or the model failed."""
    slides, filled = _fill_structure(slides)
    report = _validate(slides, command)
    if not report.blocking:
        return None
    policy = load_presentation_policy(
        command.policy_version or DEFAULT_PRESENTATION_POLICY_VERSION
    )
    blockers = [violation for violation in report.violations if violation.is_blocker]
    targets = plan_targets(TargetPlan(slides, blockers, policy, filled))
    if not targets:
        return None
    ids = tuple(target.target_id for target in targets)
    logger.info(
        LOG_GATE_REPAIR_ROUND, project_id=command.project_id, fields=len(ids), ids=ids
    )
    texts = await _ask(command, targets)
    if texts is None:
        return None
    return apply_fixes(slides, targets, texts), ids


async def run_gate_repair(command: GateRepairCommand) -> GateRepairOutcome:
    """Repair the blocked fields, at most ``max_rounds`` model calls."""
    original = copy.deepcopy(command.slides)
    slides = copy.deepcopy(command.slides)
    requested: list[tuple[str, ...]] = []
    for _ in range(command.max_rounds):
        result = await _round(slides, command)
        if result is None:
            break
        slides, ids = result
        requested.append(ids)
    slides, _ = _fill_structure(slides)
    report = _validate(slides, command)
    changed = _changed(original, slides)
    logger.info(
        LOG_GATE_REPAIR_DONE,
        project_id=command.project_id,
        rounds=len(requested),
        blocking=report.blocking,
        remaining=len(report.violations),
        changed_slides=sorted(changed),
    )
    return GateRepairOutcome(slides, report, tuple(requested), changed)


__all__ = [
    "FieldRepairRequest",
    "GateFieldRepairer",
    "GateRepairCommand",
    "GateRepairOutcome",
    "LlmGateFieldRepairer",
    "LlmGateRepairConfig",
    "parse_fixes",
    "render_field_repair_prompt",
    "run_gate_repair",
]
