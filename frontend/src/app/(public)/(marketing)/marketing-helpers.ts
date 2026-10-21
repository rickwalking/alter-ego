import type { CarouselListItem } from "@/app/(public)/(marketing)/types";
import { BLOG_LANGUAGES } from "@/constants/api";
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "@/i18n/config";
import type { SupportedLocale } from "@/i18n/config";
import { stripEmphasisMarkup } from "@/lib/public-blog-text";
import { localizedCarouselCopy } from "@/lib/public-carousels";

const LINK_MARKERS_PATTERN = /\[|\]|\(|\)/g;

/**
 * Strip lightweight markdown markers (and, AE-0412, emphasis HTML) from `text` and truncate to at most
 * `maxWords` words, appending an ellipsis when truncated. Behavior is
 * identical to the original inline helper on the marketing home page.
 */
export function truncateWords(text: string, maxWords: number): string {
  const cleaned = stripEmphasisMarkup(text.replace(LINK_MARKERS_PATTERN, ""));
  const words = cleaned.split(/\s+/).filter((w) => w.length > 0);
  if (words.length <= maxWords) return cleaned;
  return words.slice(0, maxWords).join(" ") + "...";
}

export function cardLocale(locale: string): SupportedLocale {
  return SUPPORTED_LOCALES.includes(locale as SupportedLocale)
    ? (locale as SupportedLocale)
    : DEFAULT_LOCALE;
}

export function localizedTitle(post: CarouselListItem, locale: string): string {
  return localizedCarouselCopy(post, cardLocale(locale)).title || post.topic;
}

export function localizedSubtitle(
  post: CarouselListItem,
  locale: string,
): string {
  const copy = localizedCarouselCopy(post, cardLocale(locale));
  // The topic is the Portuguese source text: only a Portuguese card uses it.
  const fallback =
    copy.language === BLOG_LANGUAGES.PORTUGUESE ? post.topic : "";
  return copy.subtitle ?? fallback;
}
