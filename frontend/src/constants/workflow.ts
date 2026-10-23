/** Phase 3 workflow, notification, and calendar API endpoints. */

export const WORKFLOW_API = {
  WORKFLOW_BOARD: "/api/workflow-board",
  WORKFLOW_BOARD_ARCHIVED: "/api/workflow-board?archived=true",
  CAROUSEL_ARCHIVE: (id: string) => `/api/carousels/${id}/archive`,
  CAROUSEL_RESTORE: (id: string) => `/api/carousels/${id}/restore`,
  NOTIFICATIONS: "/api/notifications",
  NOTIFICATION_READ: (id: string) => `/api/notifications/${id}/read`,
  ASSIGN_REVIEW: "/api/notifications/assign-review",
  CONTENT_CALENDAR: "/api/content-calendar",
  WORKFLOW_AUDIT: (type: string, id: string) =>
    `/api/workflow-audit/${type}/${id}`,
  CONTENT_LOCK: (contentId: string) => `/api/content/${contentId}/lock`,
  BLOG_SCHEDULE: (postId: string) => `/api/blog-posts/${postId}/schedule`,
  BLOG_VERSIONS: (postId: string) => `/api/blog-posts/${postId}/versions`,
} as const;

export const WORKFLOW_PHASES = [
  "brief",
  "research",
  "outline",
  "content",
  "design",
  "images",
  "final_review",
] as const;

export const WORKFLOW_PHASE_STATUS = {
  PENDING: "pending",
  IN_PROGRESS: "in_progress",
  AWAITING_HUMAN: "awaiting_human",
  APPROVED: "approved",
  REJECTED: "rejected",
  FAILED: "failed",
} as const;

export const WORKFLOW_BOARD_POLL_INTERVAL_MS = 15_000;

/** Why a board card cannot be archived, as the board API reports it (the archive route's 409s). */
export const ARCHIVE_REFUSAL = {
  PUBLISHED: "published",
  IN_PROGRESS: "in_progress",
  AUTOPILOT: "autopilot",
} as const;

/** A reason a card cannot be archived. */
export type ArchiveRefusal =
  (typeof ARCHIVE_REFUSAL)[keyof typeof ARCHIVE_REFUSAL];

export const LOCK_CONTENT_TYPE_BLOG = "blog_post";

export const HTTP_HEADER_IF_MATCH = "If-Match";

export const LOCK_POLL_INTERVAL_MS = 30_000;
