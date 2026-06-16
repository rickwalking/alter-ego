"use client";

import { useCallback, useState } from "react";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_ENDPOINTS } from "@/constants/api";

export interface SeoAnalysisResult {
  overall_score: number;
  passed: boolean;
  severity: string;
  issues: Array<{ code: string; message: string }>;
  suggestions: string[];
}

export function useSeoAnalysis(postId: string | null) {
  const [result, setResult] = useState<SeoAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(async () => {
    if (!postId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.BLOG_POST_SEO_ANALYZE(postId),
      );
      if (!response.ok) throw new Error("SEO analysis failed");
      const data = (await response.json()) as SeoAnalysisResult;
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [postId]);

  return { result, loading, error, analyze };
}
