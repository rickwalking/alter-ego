import type { MutableRefObject } from "react";
/** Notification types for the notification center. */

export type NotificationItem = {
  id: string;
  user_id: string;
  notification_type: string;
  title: string;
  body: string | null;
  status: string;
  content_id: string | null;
  content_type: string | null;
  deadline_at: string | null;
  created_at: string;
};

export type NotificationListResponse = {
  items: NotificationItem[];
  total: number;
};

export type ReviewAssignmentPayload = {
  reviewer_id: string;
  content_id: string;
  content_type: string;
  title: string;
  deadline_hours?: number;
};

export type ContentLock = {
  content_id: string;
  content_type: string;
  user_id: string;
  user_name: string;
  expires_at: string;
};

/** Which content a collaborative lock is for (AE-0446). */
export interface LockTarget {
  contentId: string;
  contentType: string;
}

/** The lock state ``useCollaborativeEdit`` keeps (AE-0446). */
export interface LockState {
  activeLock: ContentLock | null;
  isLockedByOther: boolean;
  applyLockState: (lock: ContentLock | null) => void;
  mountedRef: MutableRefObject<boolean>;
}

/** The lock actions ``useCollaborativeEdit`` exposes (AE-0446). */
export interface LockActions {
  acquireLock: () => Promise<boolean>;
  releaseLock: () => Promise<void>;
  refreshLock: () => Promise<void>;
}
