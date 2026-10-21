import type {
  BlogEditorData,
  BlogEditorValidation,
  BlogReviewActions,
  SectionSelection,
  UseBlogPostEditorResult,
} from "@/modules/publishing";
import type { DashboardBlogPost } from "@/modules/editorial-operations";

export interface BlogPostsFiltersProps {
  statusFilter: string;
  onStatusFilterChange: (value: string) => void;
  /** Posts shown after search/status filtering. */
  shownCount: number;
  /** Posts the API reports for the caller (all pages). */
  totalCount: number;
}

/** Management callbacks threaded from the page into every card. */
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

/** Field state for the editor form: labels, limits and errors. */
export interface BlogPostEditFieldsProps {
  title: string;
  onTitleChange: (value: string) => void;
  excerpt: string;
  onExcerptChange: (value: string) => void;
  validation: BlogEditorValidation;
}

export interface BlogPostEditorViewProps {
  editor: UseBlogPostEditorResult;
}

export interface BlogEditorSidebarProps {
  editor: UseBlogPostEditorResult;
  review: BlogReviewActions;
  data: BlogEditorData;
  selection: SectionSelection | null;
  /** Any image/rewrite/translation action is running. */
  slotsPending: boolean;
  onApplySuggestion: (text: string) => void;
}

export interface FieldErrorProps {
  id: string;
  message: string | null;
}

/** One dashboard list page: 0-based page plus the server-side filters. */
export interface BlogPostListQuery {
  page: number;
  status: string;
  search: string;
}

export interface BlogPostsPagerProps {
  /** 0-based current page. */
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}

export interface UseBlogPostsPagingResult {
  page: number;
  statusFilter: string;
  /** What the search box shows; the API search follows it after a pause. */
  searchInput: string;
  goToPage: (page: number) => void;
  changeStatus: (status: string) => void;
  changeSearch: (value: string) => void;
}
