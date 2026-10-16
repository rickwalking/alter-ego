"""Prompt building functions for carousel template generation."""

from rag_backend.domain.models import CarouselProject


def build_title_prompt(project: CarouselProject, research_context: str) -> str:
    from rag_backend.agents.prompts.registry import render_prompt

    prompt_text, _ = render_prompt(
        "carousel",
        "title_prompt",
        variables={
            "topic": project.topic,
            "audience": project.audience,
            "niche": project.niche,
            "research_context": research_context,
        },
        version="v2",
    )
    return prompt_text


def build_content_prompt(project: CarouselProject, research_context: str) -> str:
    from rag_backend.agents.prompts.registry import render_prompt
    from rag_backend.application.services.carousel.theme_resolver import (
        resolve_theme,
    )

    theme = resolve_theme(project)
    language_name = (
        "Brazilian Portuguese (informal but professional)"
        if project.language == "pt-BR"
        else "English (professional, direct)"
    )

    prompt_text, _ = render_prompt(
        "carousel",
        "content_prompt",
        variables={
            "topic": project.topic,
            "title": project.title,
            "subtitle": project.subtitle,
            "audience": project.audience,
            "research_context": research_context,
            "primary_color": theme["primary"],
            "accent_color": theme["accent"],
            "background_color": theme["background"],
            "language_name": language_name,
        },
        version="v2",
    )
    return prompt_text


def build_caption_prompt(
    project: CarouselProject, slide_headings: list[tuple[int, str]]
) -> str:
    """AE-0372: caption v7 (hook first, 3-5 hashtags, one CTA by goal).

    AE-0375: a "Ponto de Vista" project renders ``carousel_pov/v1/caption``
    with the slide-1 hook and the owner's thesis.
    """
    from rag_backend.agents.prompts.registry import render_prompt
    from rag_backend.domain.constants.carousel import CAROUSEL_CAPTION_PROMPT_VERSION
    from rag_backend.domain.constants.carousel_cta import DEFAULT_CTA_GOAL
    from rag_backend.domain.constants.content_mode import CONTENT_MODE_POV
    from rag_backend.domain.constants.pov_prompts import (
        POV_PROMPT_CAPTION,
        POV_PROMPT_DOMAIN,
        POV_PROMPT_VERSION,
    )

    cta_goal = project.cta_goal or DEFAULT_CTA_GOAL
    if project.content_mode == CONTENT_MODE_POV:
        hook = slide_headings[0][1] if slide_headings else project.hook_text or ""
        prompt_text, _ = render_prompt(
            POV_PROMPT_DOMAIN,
            POV_PROMPT_CAPTION,
            variables={
                "hook": hook,
                "thesis": project.pov_thesis or "",
                "slide_headings": slide_headings,
                "cta_goal": cta_goal,
            },
            version=POV_PROMPT_VERSION,
        )
        return prompt_text
    prompt_text, _ = render_prompt(
        "carousel",
        "caption_prompt",
        variables={
            "title": project.title,
            "slide_headings": slide_headings,
            "cta_goal": cta_goal,
        },
        version=CAROUSEL_CAPTION_PROMPT_VERSION,
    )
    return prompt_text


def build_slide_translation_prompt(slides_json: str, quality_rubric: str) -> str:
    """AE-0366: PT -> EN slide translation prompt (v6, carries the rubric).

    Same lazy registry import as the three builders above: the
    carousel_template.prompts -> agents.prompts.registry pair is already in the
    import-linter baseline, so no new layer edge is introduced.
    """
    from rag_backend.agents.prompts.registry import (  # integrity-ok: baselined pair
        render_prompt,
    )
    from rag_backend.domain.constants.carousel import CAROUSEL_PROMPT_VERSION_V6

    prompt_text, _ = render_prompt(
        "carousel",
        "slide_translations",
        variables={"slides_json": slides_json, "quality_rubric": quality_rubric},
        version=CAROUSEL_PROMPT_VERSION_V6,
    )
    return prompt_text


def build_autofix_retranslate_prompt(items_json: str) -> str:
    """AE-0367: re-translate the EN texts the owner autofix found untranslated.

    Same baselined lazy registry import as the builders above.
    """
    from rag_backend.agents.prompts.registry import (  # integrity-ok: baselined pair
        render_prompt,
    )
    from rag_backend.domain.constants.carousel_autofix import (
        AUTOFIX_PROMPT_DOMAIN,
        AUTOFIX_PROMPT_NAME,
        AUTOFIX_PROMPT_VERSION,
    )

    prompt_text, _ = render_prompt(
        AUTOFIX_PROMPT_DOMAIN,
        AUTOFIX_PROMPT_NAME,
        variables={"items_json": items_json},
        version=AUTOFIX_PROMPT_VERSION,
    )
    return prompt_text


def build_slide_fix_prompt(variables: dict[str, object]) -> str:
    """AE-0401: rewrite one failing slide (autopilot model fix).

    Same baselined lazy registry import as the builders above.
    """
    from rag_backend.agents.prompts.registry import (  # integrity-ok: baselined pair
        render_prompt,
    )
    from rag_backend.domain.constants.slide_fix import (
        SLIDE_FIX_PROMPT_DOMAIN,
        SLIDE_FIX_PROMPT_NAME,
        SLIDE_FIX_PROMPT_VERSION,
    )

    prompt_text, _ = render_prompt(
        SLIDE_FIX_PROMPT_DOMAIN,
        SLIDE_FIX_PROMPT_NAME,
        variables=variables,
        version=SLIDE_FIX_PROMPT_VERSION,
    )
    return prompt_text
