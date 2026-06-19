"""LinkedIn post generator.

Produces LinkedIn-optimized long-form posts in PT and EN from the
carousel's blog markdown. Voice-clones the author by feeding few-shot
examples from `WritingStyleProfile` into the system prompt.

LinkedIn limits:
- Commentary up to 3000 chars.
- Posts are rendered as plain text (no Markdown headings/bold); we keep
  output in paragraphs + line breaks only.
- First two lines get "see more" previewed, so the model is instructed
  to front-load the hook.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.application.services.writing_style_profile import (
    WritingStyleProfile,
    format_samples_for_prompt,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import LLMService
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_ERR_NO_BLOG_CONTENT = "project {} has no blog content for language {!r}"

LINKEDIN_MAX_CHARS = 3000
_LANG_EN = "en"
_LANG_PT = "pt"

# Guarded inline prompt template (AE-0243/AE-0244). This file lives in the
# `application` layer; the prompt registry lives under `agents`, so wiring it via
# `render_prompt` would create a forbidden `application -> agents` import edge
# (enforced by the import-linter contract + the down-only arch-ratchet, which must
# not be gamed). It therefore stays a guarded `_TEMPLATE` constant — the same
# sanctioned pattern as `carousel_refinement`'s `*_TEMPLATE` fallbacks (the
# `*_TEMPLATE` name is the AE-0244 checker's allowed escape). The persona and
# quality prompts (both in the `agents` layer) ARE registry-migrated by AE-0243.
_LINKEDIN_PROMPT_TEMPLATE = (
    "You are writing a LinkedIn post in {lang_name} from the blog\n"
    "content below. Match the author's voice exactly.\n"
    "\n"
    "{voice_block}\n"
    "\n"
    "Hard rules:\n"
    "- Output the post body only. No labels, no markdown, no code fences.\n"
    "- Plain text only — LinkedIn does not render markdown. Line breaks are\n"
    "  fine. Bold and italics are not.\n"
    "- First two lines must hook the reader (LinkedIn previews ~200 chars).\n"
    "- {linkedin_max_chars} character maximum including hashtags.\n"
    "- End with 3-5 relevant hashtags on a final line.\n"
    "- No em-dashes. Use commas or colons instead.\n"
    '- No generic LinkedIn clichés ("Excited to share", "I am thrilled").\n'
    "- Use short paragraphs (1-3 sentences).\n"
    "\n"
    "Post topic: {title}\n"
    "\n"
    "Source blog ({lang_name}):\n"
    "<<<\n"
    "{blog}\n"
    ">>>\n"
    "\n"
    "Write the LinkedIn post now."
)


@dataclass(frozen=True)
class _PromptInput:
    """Input data for building a LinkedIn post prompt."""

    blog: str
    language: str
    title: str
    voice_examples: str


@dataclass(frozen=True)
class LinkedInPost:
    """Generated LinkedIn post in a single language."""

    language: str
    text: str

    @property
    def char_count(self) -> int:
        return len(self.text)


class LinkedInPostGenerator:
    """Generates LinkedIn posts from a carousel's blog content."""

    def __init__(
        self,
        llm_service: LLMService,
        writing_style: WritingStyleProfile,
    ) -> None:
        self._llm = llm_service
        self._style = writing_style

    async def generate(
        self,
        project: CarouselProject,
        language: str,
    ) -> LinkedInPost:
        """Generate a LinkedIn post in the given language ('pt' or 'en')."""
        blog = _pick_blog_source(project, language)
        if not blog:
            raise ValueError(_ERR_NO_BLOG_CONTENT.format(project.id, language))
        samples = await self._style.get_samples()
        prompt = _build_prompt(
            _PromptInput(
                blog=blog,
                language=language,
                title=project.title or project.topic,
                voice_examples=format_samples_for_prompt(samples, language),
            ),
        )
        text = await self._llm.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        cleaned = _strip_leading_label(text).strip()
        truncated = _truncate_on_boundary(cleaned, LINKEDIN_MAX_CHARS)
        return LinkedInPost(language=language, text=truncated)

    async def generate_both(
        self,
        project: CarouselProject,
    ) -> tuple[LinkedInPost | None, LinkedInPost | None]:
        """Generate PT + EN posts, each skipped if its source blog is missing."""
        pt_post: LinkedInPost | None = None
        en_post: LinkedInPost | None = None
        if _pick_blog_source(project, _LANG_PT):
            pt_post = await self.generate(project, _LANG_PT)
        if _pick_blog_source(project, _LANG_EN):
            en_post = await self.generate(project, _LANG_EN)
        return pt_post, en_post


def _pick_blog_source(project: CarouselProject, language: str) -> str:
    """Return the blog body for the given language or empty string."""
    translations = project.blog_translations or {}
    if translations.get(language):
        return translations[language]
    if language == _LANG_PT and project.blog_markdown:
        return project.blog_markdown
    return ""


def _strip_leading_label(text: str) -> str:
    """Some models prefix output with 'LinkedIn Post:' — strip it."""
    for prefix in ("LinkedIn Post:", "Post:", "LinkedIn:"):
        if text.strip().lower().startswith(prefix.lower()):
            return text.strip()[len(prefix) :].strip()
    return text


def _truncate_on_boundary(text: str, max_chars: int) -> str:
    """Trim to the last sentence boundary that fits."""
    if len(text) <= max_chars:
        return text
    window = text[:max_chars]
    for sep in ("\n\n", ". ", "! ", "? ", "\n"):
        idx = window.rfind(sep)
        if idx > max_chars * 0.7:
            return window[: idx + len(sep)].rstrip()
    return window.rstrip()


def _build_prompt(
    input_data: _PromptInput,
) -> str:
    """Compose the LLM prompt for a single-language LinkedIn post."""
    lang_name = "English" if input_data.language == _LANG_EN else "Portuguese"
    voice_block = input_data.voice_examples or (
        "No voice samples available — use a direct, technical, "
        "conversational tone without corporate fluff."
    )
    return _LINKEDIN_PROMPT_TEMPLATE.format(
        lang_name=lang_name,
        voice_block=voice_block,
        linkedin_max_chars=LINKEDIN_MAX_CHARS,
        title=input_data.title,
        blog=input_data.blog,
    )
