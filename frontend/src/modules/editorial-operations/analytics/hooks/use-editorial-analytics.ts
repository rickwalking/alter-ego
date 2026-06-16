"use client";

import { useCallback, useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_ENDPOINTS } from "@/constants/api";
import type { EditorialAnalytics } from "./types";

export type {
  EditorialAnalytics,
  EditorialAnalyticsSummary,
} from "./types";

export function useEditorialAnalytics() {
  const [data, setData] = useState<EditorialAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.EDITORIAL_ANALYTICS,
      );
      if (!response.ok) throw new Error("Failed to load analytics");
      setData((await response.json()) as EditorialAnalytics);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAnalytics();
  }, [fetchAnalytics]);

  return { data, loading, error, refetch: fetchAnalytics };
}
