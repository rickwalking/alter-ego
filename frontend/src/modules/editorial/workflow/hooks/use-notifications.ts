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

async function postMarkRead(id: string, failedText: string): Promise<void> {
  const response = await authenticatedFetch(
    WORKFLOW_API.NOTIFICATION_READ(id),
    {
      method: "POST",
    },
  );
  if (!response.ok) {
    throw new Error(failedText);
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
      try {
        await postMarkRead(id, t("markReadFailed"));
      } catch {
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
