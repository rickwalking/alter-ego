import type { BlogEditorValidation } from "@/modules/publishing";
import type { DashboardBlogPost } from "@/modules/editorial-operations";

export interface BlogPostsFiltersProps {
  statusFilter: string;
  onStatusFilterChange: (value: string) => void;
  /** Posts shown after search/status filtering. */
  shownCount: number;
  /** Posts the API reports for the caller (all pages). */
  totalCount: number;
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

export interface BlogPostsListProps {
  posts: DashboardBlogPost[];
  /** No posts exist at all (vs. none matching the filters). */
  hasNoPosts: boolean;
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

/** Field state for the editor form (AE-0411): labels, limits and errors. */
export interface BlogPostEditFieldsProps {
  title: string;
  onTitleChange: (value: string) => void;
  excerpt: string;
  onExcerptChange: (value: string) => void;
  bodyText: string;
  onBodyChange: (value: string) => void;
  onSelectionChange: (value: string) => void;
  validation: BlogEditorValidation;
}

export interface FieldErrorProps {
  id: string;
  message: string | null;
}
