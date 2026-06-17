"use client";

/**
 * Hook for content calendar (UI-020).
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { WORKFLOW_API } from "@/constants/workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type { ContentCalendar } from "./types";

export function useContentCalendar(start?: string, end?: string) {
  const t = useTranslations("workflow.errors");
  const [calendar, setCalendar] = useState<ContentCalendar | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCalendar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (start) params.set("start", start);
      if (end) params.set("end", end);
      const query = params.toString() ? `?${params.toString()}` : "";
      const response = await authenticatedFetch(
        `${WORKFLOW_API.CONTENT_CALENDAR}${query}`,
      );
      if (!response.ok) {
        throw new Error(t("loadCalendarFailed"));
      }
      const data = (await response.json()) as ContentCalendar;
      setCalendar(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("unknown"));
    } finally {
      setLoading(false);
    }
  }, [start, end, t]);

  useEffect(() => {
    void fetchCalendar();
  }, [fetchCalendar]);

  return { calendar, loading, error, refetch: fetchCalendar };
}
