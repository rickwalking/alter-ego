const INLINE_MARKUP_PATTERN = /<\/?(?:strong|em|b|i)(?:\s[^>]*)?>|\*\*|__/g;

/**
 * Carousel titles come from LLM copy that may carry `**bold**`, `__underline__`
 * or `<strong>`-style tags (with or without attributes); surfaces render plain
 * text only. The empty result is the documented contract for a carousel whose
 * title and topic are both blank: callers that need a label substitute their
 * own fallback.
 */
export function stripInlineMarkup(value: string): string {
  return value.replaceAll(INLINE_MARKUP_PATTERN, "").trim();
}

/** The minimal shape every carousel label source shares. */
export interface CarouselTitleSource {
  title: string | null | undefined;
  topic: string;
}

/**
 * The single carousel display-name rule, shared by the workflow board card,
 * the create breadcrumbs, the publish heading and the workspace preview:
 * strip LLM inline markup, prefer the title, fall back to the topic.
 */
export function carouselDisplayTitle(project: CarouselTitleSource): string {
  return (
    stripInlineMarkup(project.title ?? "") || stripInlineMarkup(project.topic)
  );
}
