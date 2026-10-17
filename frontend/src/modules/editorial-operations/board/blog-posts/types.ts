import type { BlogPostOrigin, BlogPostStatus } from "@/modules/publishing";

export interface DashboardBlogPost {
  id: string;
  title: string;
  excerpt: string;
  date: string;
  views: number;
  comments: number;
  /** Provenance (AE-0296): carousel-origin posts cannot be hard-deleted. */
  origin: BlogPostOrigin;
  /** Optimistic-lock version forwarded as If-Match on mutations (AE-0296). */
  lockVersion: number;
  /**
   * Workflow status, narrowed from the API value; `null` marks an unknown
   * (drifted) backend status and renders as a neutral badge (AE-0295).
   */
  status: BlogPostStatus | null;
  /**
   * Readable by anonymous visitors right now (AE-0411). A carousel post is
   * stored `published` but stays hidden until its carousel is released, so
   * `status === "published"` alone does not mean the post is live.
   */
  isPublic: boolean;
}

export interface BlogPostBadgeVisual {
  bg: string;
  text: string;
}

/** A resolved status badge: its i18n `status.*` key and colors (AE-0411). */
export interface BlogPostBadgeLook {
  key: string;
  visual: BlogPostBadgeVisual;
}
