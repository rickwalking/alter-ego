import type { BlogPostFilters } from "@/modules/publishing";
import type { BlogPostListQuery } from "@/app/dashboard/blog-posts/types";

/** Posts per dashboard page (AE-0416); the API allows up to 100. */
export const BLOG_POSTS_PAGE_SIZE = 24;
/** Wait this long after the last keystroke before searching the API. */
export const BLOG_POSTS_SEARCH_DEBOUNCE_MS = 300;

/** Number of pages for `total` posts; at least one, so "Page 1 of 1". */
export function blogPostsPageCount(total: number): number {
  return Math.max(1, Math.ceil(total / BLOG_POSTS_PAGE_SIZE));
}

/**
 * API filters for one dashboard page (AE-0416): status and search go to the
 * server, so they cover every post, not only the page that is loaded.
 */
export function blogPostsPageFilters(
  query: BlogPostListQuery,
): BlogPostFilters {
  const search = query.search.trim();
  return {
    limit: BLOG_POSTS_PAGE_SIZE,
    offset: query.page * BLOG_POSTS_PAGE_SIZE,
    ...(query.status ? { status: query.status } : {}),
    ...(search ? { search } : {}),
  };
}
