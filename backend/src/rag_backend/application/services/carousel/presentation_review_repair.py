"""Bounded presentation repair helpers for localized slide review."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.presentation_casing import (
    repair_casing,
)
from rag_backend.application.services.carousel.presentation_copy_repair import (
    deterministic_repair_slide_payload,
    repair_body_length_and_heading,
)
from rag_backend.application.services.carousel.presentation_policy import (
    CarouselPresentationPolicy,
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_validation import (
    BoundedRepairCommand,
    BoundedRepairRequest,
    RepairFn,
    ValidatePayloadCommand,
    run_bounded_repair,
    validate_slide_payload,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation


@dataclass(frozen=True)
class LocaleRepairParams:
    """Parameters for attempting a locale repair."""

    payload: Mapping[str, object]
    locale: str
    policy: CarouselPresentationPolicy
    slide_index: int | None


SLIDE_INDEX_KEY = "slide_index"


def _deterministic_repair_for_policy(
    policy: CarouselPresentationPolicy,
) -> RepairFn:
    """Bind the policy so the deterministic repair can trim bodies to budget."""

    async def _repair(
        payload: Mapping[str, object],
        violations: tuple[SlideValidationViolation, ...],
        locale: str,
    ) -> dict[str, object]:
        await asyncio.sleep(0)
        repaired = deterministic_repair_slide_payload(payload, violations, locale)
        repaired = repair_body_length_and_heading(repaired, violations, policy)
        # AE-0312: deterministic casing repair (policy-version gated — no-op on v1).
        return repair_casing(repaired, locale, policy)

    return _repair


async def attempt_locale_repair(
    params: LocaleRepairParams,
) -> dict[str, object] | None:
    """Run one bounded repair attempt for a locale payload."""
    violations = tuple(
        validate_slide_payload(
            ValidatePayloadCommand(
                params.payload,
                locale=params.locale,
                policy=params.policy,
                slide_index=params.slide_index,
            )
        )
    )
    if not violations:
        return None
    repair_result = await run_bounded_repair(
        BoundedRepairCommand(
            request=BoundedRepairRequest(
                locale=params.locale,
                payload=params.payload,
                violations=violations,
            ),
            repair_fn=_deterministic_repair_for_policy(params.policy),
            policy=params.policy,
        )
    )
    if repair_result.violations_after:
        return None
    return dict(repair_result.payload)


async def repair_localized_slides(
    localized_slides: list[dict[str, object]],
    *,
    policy_version: str | None = None,
) -> list[dict[str, object]]:
    """Run bounded repair through run_bounded_repair for workflow orchestration."""
    active_version = policy_version or DEFAULT_PRESENTATION_POLICY_VERSION
    policy = load_presentation_policy(active_version)
    repaired_slides: list[dict[str, object]] = []
    for slide in localized_slides:
        repaired_slide = dict(slide)
        slide_index_value = slide.get(SLIDE_INDEX_KEY)
        slide_index = slide_index_value if isinstance(slide_index_value, int) else None
        for locale_key, locale in (
            (PRESENTATION_PT_KEY, LANGUAGE_PT),
            (PRESENTATION_EN_KEY, LANGUAGE_EN),
        ):
            payload = as_dict(slide.get(locale_key))
            if payload is None:
                continue
            repaired_payload = await attempt_locale_repair(
                LocaleRepairParams(
                    payload=payload,
                    locale=locale,
                    policy=policy,
                    slide_index=slide_index,
                ),
            )
            if repaired_payload is not None:
                repaired_slide[locale_key] = repaired_payload
        repaired_slides.append(repaired_slide)
    return repaired_slides


def repair_localized_slides_sync(
    localized_slides: list[dict[str, object]],
    *,
    policy_version: str | None = None,
) -> list[dict[str, object]]:
    """Sync wrapper that always routes repair through run_bounded_repair.

    When called inside a running event loop, the coroutine executes on a
    dedicated worker thread with its own loop so sync callers and async
    workflow callers share one repair implementation.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            repair_localized_slides(
                localized_slides,
                policy_version=policy_version,
            )
        )
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            asyncio.run,
            repair_localized_slides(
                localized_slides,
                policy_version=policy_version,
            ),
        )
        return future.result()


__all__ = [
    "PRESENTATION_EN_KEY",
    "PRESENTATION_PT_KEY",
    "LocaleRepairParams",
    "attempt_locale_repair",
    "repair_localized_slides",
    "repair_localized_slides_sync",
]
