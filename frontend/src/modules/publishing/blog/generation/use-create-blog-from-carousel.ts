"use client";

/**
 * "Create blog post from this carousel" (ADR-0025).
 *
 * Starts the writer (always a draft) and opens the editor on the new post. A
 * carousel that already has a post gets no duplicate: the existing post id is
 * returned so the section can link to it.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";

import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { generateBlogFromCarousel } from "./generation-requests";
import type { UseCreateBlogFromCarouselResult } from "./types";

export function useCreateBlogFromCarousel(
  projectId: string,
): UseCreateBlogFromCarouselResult {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);
  const [existingPostId, setExistingPostId] = useState<string | null>(null);

  const create = async (): Promise<void> => {
    setPending(true);
    setFailed(false);
    try {
      const result = await generateBlogFromCarousel(projectId);
      if (result.kind === "exists") {
        setExistingPostId(result.id);
        setPending(false);
        return;
      }
      router.push(DASHBOARD_ROUTES.BLOG_POST_EDIT(result.id));
    } catch {
      setFailed(true);
      setPending(false);
    }
  };

  return { pending, failed, existingPostId, create };
}
