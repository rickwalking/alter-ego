"use client";

/**
 * Hook for in-app notifications (UI-019).
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { WORKFLOW_API } from "@/constants/workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type { NotificationItem, NotificationListResponse } from "../types";

async function requestNotifications(
  unreadOnly: boolean,
  failedText: string,
): Promise<NotificationItem[]> {
  const query = unreadOnly ? "?unread_only=true" : "";
  const response = await authenticatedFetch(
    `${WORKFLOW_API.NOTIFICATIONS}${query}`,
  );
  if (!response.ok) {
    throw new Error(failedText);
  }
  const data = (await response.json()) as NotificationListResponse;
  return data.items;
}

/** True when the notification was marked read; a failed or unreachable call is false. */
async function markedRead(id: string): Promise<boolean> {
  try {
    const response = await authenticatedFetch(
      WORKFLOW_API.NOTIFICATION_READ(id),
      { method: "POST" },
    );
    return response.ok;
  } catch {
    return false;
  }
}

export function useNotifications() {
  const t = useTranslations("workflow.errors");
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = useCallback(
    async (unreadOnly = false) => {
      setLoading(true);
      setError(null);
      try {
        setNotifications(
          await requestNotifications(unreadOnly, t("loadNotificationsFailed")),
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : t("unknown"));
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  const markRead = useCallback(
    async (id: string) => {
      setError(null);
      if (!(await markedRead(id))) {
        setError(t("markReadFailed"));
        return;
      }
      setNotifications((prev) =>
        prev.map((item) =>
          item.id === id ? { ...item, status: "read" } : item,
        ),
      );
    },
    [t],
  );

  useEffect(() => {
    void fetchNotifications(true);
  }, [fetchNotifications]);

  const unreadCount = notifications.filter((n) => n.status === "unread").length;

  return {
    notifications,
    unreadCount,
    loading,
    error,
    refetch: fetchNotifications,
    markRead,
  };
}
