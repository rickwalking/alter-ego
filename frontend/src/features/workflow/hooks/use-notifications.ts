"use client";

/**
 * Hook for in-app notifications (UI-019).
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { WORKFLOW_API } from "@/constants/workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type { NotificationItem, NotificationListResponse } from "../types";

export function useNotifications() {
  const t = useTranslations("workflow.errors");
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = useCallback(async (unreadOnly = false) => {
    setLoading(true);
    setError(null);
    try {
      const query = unreadOnly ? "?unread_only=true" : "";
      const response = await authenticatedFetch(`${WORKFLOW_API.NOTIFICATIONS}${query}`);
      if (!response.ok) {
        throw new Error(t("loadNotificationsFailed"));
      }
      const data = (await response.json()) as NotificationListResponse;
      setNotifications(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("unknown"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const markRead = useCallback(async (id: string) => {
    const response = await authenticatedFetch(WORKFLOW_API.NOTIFICATION_READ(id), {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error(t("markReadFailed"));
    }
    setNotifications((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: "read" } : item)),
    );
  }, [t]);

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
