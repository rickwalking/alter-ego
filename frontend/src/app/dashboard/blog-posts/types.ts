import type { DashboardBlogPost } from "@/modules/editorial-operations";

export interface BlogPostsFiltersProps {
  statusFilter: string;
  categoryFilter: string;
  onStatusFilterChange: (value: string) => void;
  onCategoryFilterChange: (value: string) => void;
}

/** Management callbacks threaded from the page into every card (AE-0296). */
export interface BlogPostActionHandlers {
  onDelete: (post: DashboardBlogPost) => void;
  onHide: (post: DashboardBlogPost) => void;
}

export interface FeaturedBlogPostProps {
  post: DashboardBlogPost;
  actions: BlogPostActionHandlers;
}

export interface BlogPostCardProps {
  post: DashboardBlogPost;
  actions: BlogPostActionHandlers;
}

export interface BlogPostMetaProps {
  post: DashboardBlogPost;
}

export interface BlogPostCardActionsProps {
  post: DashboardBlogPost;
  actions: BlogPostActionHandlers;
}

export interface RegularBlogPostsProps {
  posts: DashboardBlogPost[];
  actions: BlogPostActionHandlers;
}

export interface DeleteConfirmModalProps {
  post: DashboardBlogPost | null;
  onConfirm: () => void;
  onCancel: () => void;
}
