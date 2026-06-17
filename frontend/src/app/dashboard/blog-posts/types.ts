import type { DashboardBlogPost } from "@/modules/editorial-operations";

export interface BlogPostsFiltersProps {
  statusFilter: string;
  categoryFilter: string;
  onStatusFilterChange: (value: string) => void;
  onCategoryFilterChange: (value: string) => void;
}

export interface FeaturedBlogPostProps {
  post: DashboardBlogPost;
}

export interface BlogPostCardProps {
  post: DashboardBlogPost;
}

export interface BlogPostMetaProps {
  post: DashboardBlogPost;
}

export interface RegularBlogPostsProps {
  posts: DashboardBlogPost[];
}
