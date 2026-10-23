/** Allowed URL schemes for markdown links rendered on public pages. */
export const MARKDOWN_LINK_ALLOWED_SCHEMES = [
  "http:",
  "https:",
  "mailto:",
] as const;

/** `//host` or `/\\host`: another site, despite the leading slash. */
const PROTOCOL_RELATIVE = /^[/\\]{2}/;

/** Tab, line feed and carriage return: a browser drops them anywhere in a URL. */
const URL_DROPPED_CHARS = /[\t\n\r]/g;

/** Code points up to space: a browser trims them from both ends of a URL. */
const MAX_TRIMMED_CODE_POINT = 0x20;

function isTrimmedByUrlParser(char: string | undefined): boolean {
  return char !== undefined && char.charCodeAt(0) <= MAX_TRIMMED_CODE_POINT;
}

/**
 * The href as a browser reads it (WHATWG URL parsing): tabs and newlines
 * removed, control characters and spaces trimmed from both ends. Checks and
 * rendering both use this form, so `/\t/evil.test` is seen as `//evil.test`.
 */
export function normalizeMarkdownHref(href: string): string {
  const kept = href.replace(URL_DROPPED_CHARS, "");
  let start = 0;
  let end = kept.length;
  while (start < end && isTrimmedByUrlParser(kept[start])) start += 1;
  while (end > start && isTrimmedByUrlParser(kept[end - 1])) end -= 1;
  return kept.slice(start, end);
}

/**
 * Returns true when href is safe to render as a clickable link (blocks javascript:, data:, etc.).
 */
export function isSafeMarkdownHref(href: string | undefined): boolean {
  if (href === undefined) {
    return false;
  }
  const trimmed = normalizeMarkdownHref(href);
  if (trimmed.length === 0) {
    return false;
  }
  if (PROTOCOL_RELATIVE.test(trimmed)) {
    return false;
  }
  if (trimmed.startsWith("/") || trimmed.startsWith("#")) {
    return true;
  }
  try {
    const url = new URL(trimmed);
    return MARKDOWN_LINK_ALLOWED_SCHEMES.includes(
      url.protocol as (typeof MARKDOWN_LINK_ALLOWED_SCHEMES)[number],
    );
  } catch {
    return false;
  }
}
