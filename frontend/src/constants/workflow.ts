/** Phase 3 workflow, notification, and calendar API endpoints. */

export const WORKFLOW_API = {
  WORKFLOW_BOARD: "/api/workflow-board",
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
} as const;

export const WORKFLOW_BOARD_POLL_INTERVAL_MS = 15_000;

export const LOCK_CONTENT_TYPE_BLOG = "blog_post";
export const LOCK_CONTENT_TYPE_CAROUSEL = "carousel";

export const HTTP_HEADER_IF_MATCH = "If-Match";

export const LOCK_POLL_INTERVAL_MS = 30_000;
