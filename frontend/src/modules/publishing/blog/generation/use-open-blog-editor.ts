"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { generateBlogFromCarousel } from "./generation-requests";
import type { UseOpenBlogEditorResult } from "./types";

/**
 * Open the carousel's blog post in the blog editor. The carousel's existing
 * post opens directly; a carousel without one gets its draft written first
 * (ADR-0025), then the editor opens on it.
 */
export function useOpenBlogEditor(projectId: string): UseOpenBlogEditorResult {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  const open = async (): Promise<void> => {
    setPending(true);
    setFailed(false);
    try {
      const result = await generateBlogFromCarousel(projectId);
      router.push(DASHBOARD_ROUTES.BLOG_POST_EDIT(result.id));
    } catch {
      setFailed(true);
      setPending(false);
    }
  };

  return { pending, failed, open };
}
