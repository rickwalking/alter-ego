"use client";

import { useCallback, useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_ENDPOINTS, HTTP_STATUS } from "@/constants/api";
import type { EditorialAnalytics, EditorialAnalyticsState } from "./types";

export type {
  EditorialAnalytics,
  EditorialAnalyticsState,
  EditorialAnalyticsSummary,
} from "./types";

/**
 * The route answers 404 when the editorial-analytics flag is off and
 * 403 for a role without access. Both are a "disabled" state, not an error.
 */
const ANALYTICS_DISABLED_STATUSES: ReadonlySet<number> = new Set([
  HTTP_STATUS.FORBIDDEN,
  HTTP_STATUS.NOT_FOUND,
]);
const ERR_ANALYTICS_LOAD_FAILED = "Failed to load analytics";
const ERR_UNKNOWN = "Unknown error";

export function useEditorialAnalytics(): EditorialAnalyticsState {
  const [data, setData] = useState<EditorialAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [disabled, setDisabled] = useState(false);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.EDITORIAL_ANALYTICS,
      );
      if (ANALYTICS_DISABLED_STATUSES.has(response.status)) {
        setDisabled(true);
        setData(null);
        return;
      }
      if (!response.ok) throw new Error(ERR_ANALYTICS_LOAD_FAILED);
      setDisabled(false);
      setData((await response.json()) as EditorialAnalytics);
    } catch (err) {
      setError(err instanceof Error ? err.message : ERR_UNKNOWN);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAnalytics();
  }, [fetchAnalytics]);

  return { data, loading, error, disabled, refetch: fetchAnalytics };
}
