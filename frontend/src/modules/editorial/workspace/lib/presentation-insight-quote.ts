/**
 * AE-0407: the ``pov_news`` quote card stored under a slide locale's
 * ``insight`` key (backend ``domain/news_quote_cards.py`` ``quote_card``).
 */

/** The structured-extra key that carries the quote card. */
export const INSIGHT_QUOTE_EXTRA_KEY = "insight";
/** Prefix of a social handle (``@taylorhbuilds``). */
export const QUOTE_HANDLE_PREFIX = "@";
/** The platform every ``pov_news`` quote comes from (brand name, not translated). */
export const QUOTE_SOURCE_PLATFORM = "X";

/** The raw ``insight`` payload; any extra key (e.g. a url) is ignored. */
export interface PresentationInsightQuotePayload {
  quote: string;
  handle: string;
  name?: string;
  attribution?: string;
  quote_id?: string;
}

/** The display shape of a quote card (no url, ever). */
export interface PresentationInsightQuote {
  quote: string;
  name: string;
  handle: string;
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

export function isPresentationInsightQuotePayload(
  value: unknown,
): value is PresentationInsightQuotePayload {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    nonEmptyString(record.quote) &&
    nonEmptyString(record.handle) &&
    (nonEmptyString(record.name) || nonEmptyString(record.attribution))
  );
}

/** ``taylorhbuilds`` and ``@taylorhbuilds`` both become ``@taylorhbuilds``. */
export function formatQuoteHandle(handle: string): string {
  const bare = handle.trim().replace(/^@+/, "");
  return `${QUOTE_HANDLE_PREFIX}${bare}`;
}

/** The display card for a valid payload, or ``null`` (JSON fallback). */
export function parsePresentationInsightQuote(
  value: unknown,
): PresentationInsightQuote | null {
  if (!isPresentationInsightQuotePayload(value)) {
    return null;
  }
  const name = nonEmptyString(value.name) ? value.name : value.attribution;
  return {
    quote: value.quote.trim(),
    name: (name ?? "").trim(),
    handle: formatQuoteHandle(value.handle),
  };
}
