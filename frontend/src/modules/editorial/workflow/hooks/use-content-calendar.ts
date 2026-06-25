"use client";

/**
 * Hook for content calendar (UI-020).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { WORKFLOW_API } from "@/constants/workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type { ContentCalendar } from "./types";

function buildCalendarUrl(start?: string, end?: string): string {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const query = params.toString() ? `?${params.toString()}` : "";
  return `${WORKFLOW_API.CONTENT_CALENDAR}${query}`;
}

export function useContentCalendar(start?: string, end?: string) {
  const t = useTranslations("workflow.errors");
  const [calendar, setCalendar] = useState<ContentCalendar | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Tracks the in-flight request so a slower stale response (e.g. after fast
  // month navigation) can never overwrite the latest window's result.
  const controllerRef = useRef<AbortController | null>(null);

  const fetchCalendar = useCallback(async () => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const isCurrent = (): boolean => controllerRef.current === controller;
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(buildCalendarUrl(start, end), {
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(t("loadCalendarFailed"));
      }
      const data = (await response.json()) as ContentCalendar;
      if (isCurrent()) setCalendar(data);
    } catch (err) {
      if (controller.signal.aborted || !isCurrent()) return;
      setError(err instanceof Error ? err.message : t("unknown"));
    } finally {
      if (isCurrent()) setLoading(false);
    }
  }, [start, end, t]);

  useEffect(() => {
    void fetchCalendar();
    return () => controllerRef.current?.abort();
  }, [fetchCalendar]);

  return { calendar, loading, error, refetch: fetchCalendar };
}
