/**
 * Blog post domain constants (AE-0295).
 *
 * `BLOG_POST_STATUSES` mirrors the backend `BlogPostStatus` StrEnum
 * (`backend/src/rag_backend/domain/constants/blog_post.py`) — the backend is
 * the source of truth; a contract test asserts the two stay identical.
 */

export const BLOG_POST_STATUSES = [
  "draft",
  "under_review",
  "approved",
  "published",
  "archived",
] as const;

export type BlogPostStatus = (typeof BLOG_POST_STATUSES)[number];

export function toBlogPostStatus(value: string): BlogPostStatus | null {
  return (BLOG_POST_STATUSES as readonly string[]).includes(value)
    ? (value as BlogPostStatus)
    : null;
}

/**
 * Blog post provenance (AE-0296) — mirrors the backend `BlogPostOrigin`
 * StrEnum. Carousel-origin rows back the public carousel blog projection and
 * cannot be hard-deleted while linked to their project.
 */
export const BLOG_POST_ORIGINS = ["standalone", "carousel"] as const;

export type BlogPostOrigin = (typeof BLOG_POST_ORIGINS)[number];

export const BLOG_POST_ORIGIN_STANDALONE: BlogPostOrigin = "standalone";
export const BLOG_POST_ORIGIN_CAROUSEL: BlogPostOrigin = "carousel";

export function toBlogPostOrigin(
  value: string | null | undefined,
): BlogPostOrigin {
  return value === BLOG_POST_ORIGIN_CAROUSEL
    ? BLOG_POST_ORIGIN_CAROUSEL
    : BLOG_POST_ORIGIN_STANDALONE;
}

/** Backend mutation-guard error details surfaced to the UI (AE-0296). */
export const BLOG_POST_ERR_VERSION_CONFLICT = "version_conflict";
export const BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED =
  "carousel_origin_delete_blocked";

export type BlogPostMutationErrorCode =
  | typeof BLOG_POST_ERR_VERSION_CONFLICT
  | typeof BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED;

/** Error carrying the backend guard detail so the UI can map it to copy. */
export class BlogPostMutationError extends Error {
  constructor(public readonly code: BlogPostMutationErrorCode) {
    super(code);
    this.name = "BlogPostMutationError";
  }
}
