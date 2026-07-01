import type { BlogPostFilters, DashboardBlogPost } from "./types";

export function formatBlogPostDate(date: string): string {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function filterBlogPosts(
  posts: DashboardBlogPost[],
  filters: BlogPostFilters,
): DashboardBlogPost[] {
  const searchLower = filters.search.toLowerCase();
  const statusLower = filters.statusFilter.toLowerCase();
  const categoryLower = filters.categoryFilter.toLowerCase();

  return posts.filter((post) => {
    // Status filter matches the workflow status, not the content category
    // (conflating the two was the AE-0295 root cause).
    if (statusLower && (post.status ?? "") !== statusLower) {
      return false;
    }
    if (categoryLower && post.category.toLowerCase() !== categoryLower) {
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
