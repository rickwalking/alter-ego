"use client";

/**
 * The editor's view of a post's generation run.
 *
 * Shares the editor's detail query (same key) and re-reads it every
 * `GENERATION_POLL_INTERVAL_MS` while the run is in progress, so the sections
 * appear in the editor as soon as the backend stores them. `retry` starts a
 * new attempt on the same row and refreshes the post.
 */

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { blogPostKeys, fetchBlogPostDetail } from "../blog-post-requests";
import type { BlogPost } from "../types";
import {
  GENERATION_POLL_INTERVAL_MS,
  GENERATION_STATUS,
} from "./generation-constants";
import { retryBlogGeneration } from "./generation-requests";
import { readGenerationState } from "./generation-state";
import type { UseBlogGenerationResult } from "./types";

/** Poll interval while running, `false` once the run has settled. */
export function generationPollInterval(
  post: BlogPost | null | undefined,
): number | false {
  const state = readGenerationState(post?.ai_generation_metadata);
  return state?.status === GENERATION_STATUS.IN_PROGRESS
    ? GENERATION_POLL_INTERVAL_MS
    : false;
}

export function useBlogGeneration(postId: string): UseBlogGenerationResult {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: blogPostKeys.detail(postId),
    queryFn: () => fetchBlogPostDetail(postId),
    enabled: Boolean(postId),
    refetchInterval: (current) => generationPollInterval(current.state.data),
  });
  const [retrying, setRetrying] = useState(false);
  const [retryFailed, setRetryFailed] = useState(false);

  const retry = async (): Promise<void> => {
    setRetrying(true);
    setRetryFailed(false);
    try {
      await retryBlogGeneration(postId);
      await queryClient.invalidateQueries({
        queryKey: blogPostKeys.detail(postId),
      });
    } catch {
      setRetryFailed(true);
    } finally {
      setRetrying(false);
    }
  };

  return {
    state: readGenerationState(query.data?.ai_generation_metadata),
    projectId: query.data?.project_id ?? null,
    retrying,
    retryFailed,
    retry,
  };
}
