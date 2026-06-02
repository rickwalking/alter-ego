/** Allowed URL schemes for markdown links rendered on public pages. */
export const MARKDOWN_LINK_ALLOWED_SCHEMES = [
  "http:",
  "https:",
  "mailto:",
] as const;

/**
 * Returns true when href is safe to render as a clickable link (blocks javascript:, data:, etc.).
 */
export function isSafeMarkdownHref(href: string | undefined): boolean {
  if (href === undefined || href === null) {
    return false;
  }
  const trimmed = href.trim();
  if (trimmed.length === 0) {
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
