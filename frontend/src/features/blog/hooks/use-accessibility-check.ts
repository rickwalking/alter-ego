"use client";

import { useCallback, useState } from "react";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_ENDPOINTS } from "@/constants/api";

export interface AccessibilityIssue {
  code: string;
  message: string;
  severity: string;
}

export interface AccessibilityResult {
  overall_score: number;
  passed: boolean;
  severity: string;
  issues: AccessibilityIssue[];
}

export function useAccessibilityCheck(postId: string | null) {
  const [result, setResult] = useState<AccessibilityResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const check = useCallback(async () => {
    if (!postId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.BLOG_POST_ACCESSIBILITY_CHECK(postId),
      );
      if (!response.ok) throw new Error("Accessibility check failed");
      const data = (await response.json()) as AccessibilityResult;
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [postId]);

  return { result, loading, error, check };
}
