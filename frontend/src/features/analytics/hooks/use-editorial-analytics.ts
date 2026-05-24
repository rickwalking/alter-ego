"use client";

import { useCallback, useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_ENDPOINTS } from "@/constants/api";

export interface EditorialAnalyticsSummary {
  total_posts: number;
  published_this_week: number;
  published_this_month: number;
  content_velocity_per_week: number;
  status_breakdown: Record<string, number>;
  average_views: number;
  pending_review: number;
  draft_count: number;
  quality_score_average: number;
}

export interface EditorialAnalytics {
  summary: EditorialAnalyticsSummary;
  velocity_by_week: Array<{ week_start: string; published_count: number }>;
}

export function useEditorialAnalytics() {
  const [data, setData] = useState<EditorialAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(API_ENDPOINTS.EDITORIAL_ANALYTICS);
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
