/** Phase 3 workflow, notification, and calendar API endpoints. */

export const WORKFLOW_API = {
  WORKFLOW_BOARD: "/api/workflow-board",
  WORKFLOW_BOARD_ARCHIVED: "/api/workflow-board?archived=true",
  CAROUSEL_ARCHIVE: (id: string) => `/api/carousels/${id}/archive`,
  CAROUSEL_RESTORE: (id: string) => `/api/carousels/${id}/restore`,
  CAROUSEL_REPROCESS: (id: string) => `/api/carousels/${id}/workflow/reprocess`,
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

/** URL query param marking the archived board view (`?archived=1`). */
export const WORKFLOW_BOARD_ARCHIVED_PARAM = "archived";

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

/** Generation queue panel endpoints (admin only). */
export const QUEUE_API = {
  BOARD: "/api/generation-runs",
  RETRY: (id: string) => `/api/generation-runs/${id}/retry`,
  DISCARD: (id: string) => `/api/generation-runs/${id}/discard`,
  CANCEL: (id: string) => `/api/generation-runs/${id}/cancel`,
  REPROCESS: (id: string) => `/api/generation-runs/${id}/reprocess`,
  PROCESS: "/api/generation-runs/process",
  GENERATE_NOW: (id: string) => `/api/generation-runs/backlog/${id}/generate`,
} as const;

/** Statuses of a generation run on the queue panel. */
export const QUEUE_STATUS = {
  QUEUED: "queued",
  RUNNING: "running",
  RETRY_WAIT: "retry_wait",
  DEAD_LETTER: "dead_letter",
} as const;

/** The panel buttons. */
export const QUEUE_ACTION = {
  RETRY: "retry",
  DISCARD: "discard",
  CANCEL: "cancel",
  REPROCESS: "reprocess",
  GENERATE_NOW: "generateNow",
} as const;

export type QueueAction = (typeof QUEUE_ACTION)[keyof typeof QUEUE_ACTION];

export const REPROCESS_REFUSAL = {
  STALE_VERSION: "stale_expected_version",
  OWNER_WAITING: "owner_waiting",
  NORMAL_QUEUED: "normal_queued",
  DISPATCHER_GRACE: "dispatcher_grace",
  FRESH_RUNNING: "fresh_running",
  NULL_HEARTBEAT: "null_heartbeat",
  DRIVE_ACTIVE: "drive_active",
  UNSUPPORTED: "unsupported",
  PROJECTLESS_UNSTAGED: "projectless_unstaged",
  CONCURRENT_UPDATE: "concurrent_update",
} as const;

export const REPROCESS_REFUSAL_CODES: ReadonlySet<string> = new Set(
  Object.values(REPROCESS_REFUSAL),
);

export const REPROCESS_POLL_INTERVAL_MS = 2_000;
