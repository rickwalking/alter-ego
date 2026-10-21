import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "./config";
import type { SupportedLocale } from "./config";

/** Cookie the LanguageSwitcher writes; an explicit choice wins. */
export const LOCALE_COOKIE = "locale";
export const ACCEPT_LANGUAGE_HEADER = "accept-language";

const DEFAULT_QUALITY = 1;
const QUALITY_PARAM = /^q=([0-9.]+)$/i;

export interface LocaleSources {
  cookie: string | undefined;
  acceptLanguage: string | null | undefined;
}

interface WeightedLanguage {
  language: string;
  quality: number;
}

export function isSupportedLocale(
  value: string | undefined,
): value is SupportedLocale {
  return SUPPORTED_LOCALES.includes(value as SupportedLocale);
}

function parseQuality(params: string[]): number {
  for (const param of params) {
    const match = QUALITY_PARAM.exec(param.trim());
    if (match) {
      return Number(match[1]);
    }
  }
  return DEFAULT_QUALITY;
}

/** Weighted primary languages of a header ("pt-BR" -> "pt": one file per primary language). */
function parseAcceptLanguage(header: string): WeightedLanguage[] {
  return header
    .split(",")
    .map((entry) => {
      const [tag = "", ...params] = entry.split(";");
      const language = tag.trim().toLowerCase().split("-")[0] ?? "";
      return { language, quality: parseQuality(params) };
    })
    .filter((item) => item.language !== "" && item.quality > 0);
}

/**
 * Best supported language of an Accept-Language header, by quality. The sort is
 * stable, so equal qualities keep the header order.
 */
export function matchAcceptLanguage(
  header: string | null | undefined,
): SupportedLocale | null {
  if (!header) {
    return null;
  }
  const ranked = parseAcceptLanguage(header).sort(
    (left, right) => right.quality - left.quality,
  );
  const match = ranked.find((item) => isSupportedLocale(item.language));
  return match ? (match.language as SupportedLocale) : null;
}

/**
 * The request locale is the `locale` cookie when it is valid, else
 * the best supported Accept-Language match, else the default.
 */
export function resolveLocale(sources: LocaleSources): SupportedLocale {
  if (isSupportedLocale(sources.cookie)) {
    return sources.cookie;
  }
  return matchAcceptLanguage(sources.acceptLanguage) ?? DEFAULT_LOCALE;
}
