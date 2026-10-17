import { formatLocaleDate } from "@/lib/locale-format";
import type { BlogPostFilters, DashboardBlogPost } from "./types";

/** Card date in the active locale (AE-0417: pt "17/10/2026", en "Oct 17, 2026"). */
export function formatBlogPostDate(date: string, locale: string): string {
  return formatLocaleDate(date, locale);
}

/**
 * The one post shown in the large "featured" slot: the newest post that is
 * actually live (AE-0411). Every other post renders as a regular card, so no
 * post is ever dropped from the list (B07).
 */
export function pickFeaturedBlogPost(
  posts: DashboardBlogPost[],
): DashboardBlogPost | undefined {
  return posts.find((post) => post.isPublic);
}

export function filterBlogPosts(
  posts: DashboardBlogPost[],
  filters: BlogPostFilters,
): DashboardBlogPost[] {
  const searchLower = filters.search.toLowerCase();
  const statusLower = filters.statusFilter.toLowerCase();

  return posts.filter((post) => {
    // Status filter matches the workflow status, not the content category
    // (conflating the two was the AE-0295 root cause).
    if (statusLower && (post.status ?? "") !== statusLower) {
      return false;
    }
    if (
      searchLower &&
      !post.title.toLowerCase().includes(searchLower) &&
      !post.excerpt.toLowerCase().includes(searchLower)
    ) {
      return false;
    }
    return true;
  });
}
