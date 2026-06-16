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
    if (statusLower && post.category.toLowerCase() !== statusLower) {
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
