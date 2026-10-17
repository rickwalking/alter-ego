import type { BlogPostFilters, DashboardBlogPost } from "./types";

export function formatBlogPostDate(date: string): string {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
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
