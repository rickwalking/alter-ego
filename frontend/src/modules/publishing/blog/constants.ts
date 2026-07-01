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
