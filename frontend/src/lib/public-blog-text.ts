/**
 * Text helpers for the public blog surfaces (AE-0412, QA 2026-10-16 B21/B22).
 *
 * Generated carousel copy carries emphasis markup (`<strong>`, `**`) and, on
 * some projects, placeholder titles such as "slide". Public pages must never
 * show that markup raw, nor a placeholder as a title.
 */

import type { SupportedLocale } from "@/i18n/config";
import { formatLocaleDate } from "@/lib/locale-format";

const EMPHASIS_TAG_PATTERN = /<\/?(?:strong|b|em|i)\s*>/gi;
const STRONG_HTML_PATTERN = /<(strong|b)\s*>([\s\S]*?)<\/\1\s*>/gi;
const EM_HTML_PATTERN = /<(em|i)\s*>([\s\S]*?)<\/\1\s*>/gi;
const MARKDOWN_EMPHASIS_PATTERN = /\*\*|__|\*|`/g;
const WHITESPACE_PATTERN = /\s+/g;

/** Titles the pipeline writes when no real heading exists (slide types). */
const PLACEHOLDER_TITLES: ReadonlySet<string> = new Set([
  "slide",
  "untitled",
  "hook",
  "intro",
  "content",
  "cta",
  "closing",
  "conclusion",
  "summary",
]);
const NUMBERED_SLIDE_PATTERN = /^slide[\s_-]*\d*$/i;

/** A category chip longer than this is a sentence, not a category. */
const CATEGORY_MAX_CHARS = 32;
const CATEGORY_MAX_WORDS = 4;

/** Public dates are calendar dates of the stored UTC instant. */
const PUBLIC_DATE_TIME_ZONE = "UTC";

/** Remove emphasis markup (HTML and markdown) and collapse whitespace. */
export function stripEmphasisMarkup(text: string): string {
  return text
    .replace(EMPHASIS_TAG_PATTERN, "")
    .replace(MARKDOWN_EMPHASIS_PATTERN, "")
    .replace(WHITESPACE_PATTERN, " ")
    .trim();
}

/** Convert inline emphasis HTML to markdown so the body renders it safely. */
export function emphasisHtmlToMarkdown(markdown: string): string {
  return markdown
    .replace(STRONG_HTML_PATTERN, "**$2**")
    .replace(EM_HTML_PATTERN, "*$2*")
    .replace(EMPHASIS_TAG_PATTERN, "");
}

export function isPlaceholderTitle(title: string): boolean {
  const normalized = stripEmphasisMarkup(title).toLowerCase();
  if (!normalized) {
    return true;
  }
  return (
    PLACEHOLDER_TITLES.has(normalized) ||
    NUMBERED_SLIDE_PATTERN.test(normalized)
  );
}

/** First candidate that is a real title, without markup; "" when none is. */
export function resolveDisplayTitle(
  candidates: readonly (string | null | undefined)[],
): string {
  for (const candidate of candidates) {
    if (candidate && !isPlaceholderTitle(candidate)) {
      return stripEmphasisMarkup(candidate);
    }
  }
  return "";
}

/** A short category label, or undefined when the niche is missing or a sentence. */
export function toCategoryLabel(
  niche: string | null | undefined,
): string | undefined {
  const label = stripEmphasisMarkup(niche ?? "");
  if (!label || label.length > CATEGORY_MAX_CHARS) {
    return undefined;
  }
  return label.split(" ").length > CATEGORY_MAX_WORDS ? undefined : label;
}

/** Locale-aware date (pt: 14/10/2026, en: Oct 14, 2026); "" for invalid input. */
export function formatPublicDate(
  isoDate: string | null | undefined,
  locale: SupportedLocale,
): string {
  return formatLocaleDate(isoDate, locale, PUBLIC_DATE_TIME_ZONE);
}
