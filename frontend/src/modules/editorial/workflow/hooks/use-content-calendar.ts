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

/** GET the calendar window; a non-OK status throws ``failedText``. */
async function requestCalendar(
  url: string,
  signal: AbortSignal,
  failedText: string,
): Promise<ContentCalendar> {
  const response = await authenticatedFetch(url, { signal });
  if (!response.ok) {
    throw new Error(failedText);
  }
  return (await response.json()) as ContentCalendar;
}

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

/**
 * The in-flight request is tracked so a slower stale response (e.g. after fast
 * month navigation) never overwrites the latest window's result; cleanup aborts
 * and clears it so a superseded request's `finally` cannot write state after
 * unmount. `enabled: false` skips the fetch (e.g. until the window is known).
 */
export function useContentCalendar(
  start?: string,
  end?: string,
  enabled = true,
) {
  const t = useTranslations("workflow.errors");
  const [calendar, setCalendar] = useState<ContentCalendar | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const fetchCalendar = useCallback(async () => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const isCurrent = (): boolean => controllerRef.current === controller;
    setLoading(true);
    setError(null);
    try {
      const data = await requestCalendar(
        buildCalendarUrl(start, end),
        controller.signal,
        t("loadCalendarFailed"),
      );
      if (isCurrent()) setCalendar(data);
    } catch (err) {
      if (controller.signal.aborted || !isCurrent()) return;
      setError(errorMessage(err, t("unknown")));
    } finally {
      if (isCurrent()) setLoading(false);
    }
  }, [start, end, t]);

  useEffect(() => {
    if (!enabled) {
      return undefined;
    }
    void fetchCalendar();
    return () => {
      controllerRef.current?.abort();
      controllerRef.current = null;
    };
  }, [fetchCalendar, enabled]);

  return { calendar, loading, error, refetch: fetchCalendar };
}
