import {
  blogDocumentSchema,
  BLOG_SCHEMA_V2,
  type BlogDocument,
  type BlogLanguageDocument,
} from "@/schemas/blog-document";

/**
 * Strict `blog.v2` parse helper (ADR-0025) — the frontend mirror of
 * the backend `parse_blog_content`. There is no v1 branch: a legacy markdown
 * blob, a JSON array or any other `schema` is rejected. The backend read
 * fail-safe adapts a non-migrated row before the API, so the public page
 * only ever needs v2.
 */

export const ERR_BLOG_DOCUMENT_NOT_V2 = "blog_document_not_v2";
export const ERR_INVALID_BLOG_DOCUMENT = "invalid_blog_document";

export class InvalidBlogDocumentError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(code);
    this.name = "InvalidBlogDocumentError";
    this.code = code;
  }
}

function hasV2Marker(content: unknown): boolean {
  if (!content || typeof content !== "object" || Array.isArray(content)) {
    return false;
  }
  return (content as Record<string, unknown>).schema === BLOG_SCHEMA_V2;
}

/** Validate `content` as `blog.v2` or throw `InvalidBlogDocumentError`. */
export function parseBlogContent(content: unknown): BlogDocument {
  if (!hasV2Marker(content)) {
    throw new InvalidBlogDocumentError(ERR_BLOG_DOCUMENT_NOT_V2);
  }
  const parsed = blogDocumentSchema.safeParse(content);
  if (!parsed.success) {
    throw new InvalidBlogDocumentError(ERR_INVALID_BLOG_DOCUMENT);
  }
  return parsed.data;
}

/** Like `parseBlogContent`, but `null` instead of throwing (fail-safe pages). */
export function tryParseBlogContent(content: unknown): BlogDocument | null {
  try {
    return parseBlogContent(content);
  } catch {
    return null;
  }
}

function hasBody(document: BlogLanguageDocument): boolean {
  return document.sections.some((section) => section.body_md.trim() !== "");
}

/**
 * The language subtree to render: `translations[lang]` when it has at least
 * one non-empty section, else the canonical PT document (a missing or blank
 * translation never renders an empty page and never 404s, as in v1).
 */
export function resolveBlogLanguage(
  document: BlogDocument,
  lang: string,
): BlogLanguageDocument {
  const translation = document.translations[lang];
  return translation && hasBody(translation) ? translation : document;
}
