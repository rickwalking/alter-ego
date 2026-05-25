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
        version="v1",
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
        version="v1",
    )
    return prompt_text


def build_caption_prompt(project: CarouselProject, slide_headings: list[tuple[int, str]]) -> str:
    from rag_backend.agents.prompts.registry import render_prompt

    prompt_text, _ = render_prompt(
        "carousel",
        "caption_prompt",
        variables={
            "title": project.title,
            "slide_headings": slide_headings,
        },
        version="v1",
    )
    return prompt_text
