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
