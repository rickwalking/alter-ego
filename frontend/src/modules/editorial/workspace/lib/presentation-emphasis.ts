/**
 * The per-locale emphasis convention of slide copy:
 * PT copy marks emphasis with ``**texto**``, EN copy with
 * ``<strong>text</strong>``. The content review shows the convention as a hint
 * and flags (and can convert) copy written with the other locale's markup.
 */
import type { PresentationLocaleKey } from "./presentation-slide-resolution";

const PT_LOCALE: PresentationLocaleKey = "presentation_pt";

/** The markup example shown in each locale's hint (an ICU variable, not text). */
export const EMPHASIS_EXAMPLE_BY_LOCALE: Readonly<
  Record<PresentationLocaleKey, string>
> = {
  presentation_pt: "**…**",
  presentation_en: "<strong>…</strong>",
};

const STRONG_TAG_PAIR = /<strong>([\s\S]*?)<\/strong>/gi;
const STRONG_TAG = /<\/?strong>/i;
const DOUBLE_STAR_PAIR = /\*\*([\s\S]+?)\*\*/g;
const DOUBLE_STAR = "**";

/** True when ``value`` uses the OTHER locale's emphasis markup. */
export function emphasisConventionMismatch(
  locale: PresentationLocaleKey,
  value: string,
): boolean {
  return locale === PT_LOCALE
    ? STRONG_TAG.test(value)
    : value.includes(DOUBLE_STAR);
}

/** Rewrite balanced emphasis into the locale's convention (text unchanged). */
export function normalizeEmphasis(
  locale: PresentationLocaleKey,
  value: string,
): string {
  return locale === PT_LOCALE
    ? value.replace(STRONG_TAG_PAIR, "**$1**")
    : value.replace(DOUBLE_STAR_PAIR, "<strong>$1</strong>");
}
