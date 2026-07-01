import type { BlogPostStatus } from "@/modules/publishing";

export interface DashboardBlogPost {
  id: string;
  title: string;
  excerpt: string;
  date: string;
  views: number;
  comments: number;
  /**
   * Workflow status, narrowed from the API value; `null` marks an unknown
   * (drifted) backend status and renders as a neutral badge (AE-0295).
   */
  status: BlogPostStatus | null;
  /** Content category — a distinct domain from status; unpopulated today. */
  category: string;
  featured: boolean;
}

export interface BlogPostBadgeVisual {
  bg: string;
  text: string;
}

export interface BlogPostFilters {
  search: string;
  statusFilter: string;
  categoryFilter: string;
}
