import { useEffect, useRef } from "react";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { API_ENDPOINTS } from "@/constants/api";
import { apiCall } from "@/lib/api-client";
import { carouselKeys } from "@/modules/carousel-presentation";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";
import { carouselGenerationLogResponseSchema } from "@/schemas/carousel-generation-log";
import type { GenerationLogView } from "./types";

const GENERATION_LOG_KEY = "generation-log";

function generationLogKey(projectId: string) {
  return [...carouselKeys.detail(projectId), GENERATION_LOG_KEY] as const;
}

function generationLogUrl(
  projectId: string,
  before: string | undefined,
): string {
  const base = API_ENDPOINTS.CAROUSEL_GENERATION_LOG(projectId);
  return before === undefined
    ? base
    : `${base}?before=${encodeURIComponent(before)}`;
}

/** One cursor-paginated log, refreshed only by existing workflow updates. */
export function useGenerationLog(
  projectId: string,
  workflowState: EditorialWorkflowState | null,
): GenerationLogView {
  const queryClient = useQueryClient();
  const previous = useRef({ projectId, state: workflowState });
  const query = useInfiniteQuery({
    queryKey: generationLogKey(projectId),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      apiCall(
        generationLogUrl(projectId, pageParam),
        carouselGenerationLogResponseSchema,
      ),
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });

  useEffect(() => {
    const current = previous.current;
    if (current.projectId === projectId && current.state !== workflowState) {
      void queryClient.invalidateQueries({
        queryKey: generationLogKey(projectId),
      });
    }
    previous.current = { projectId, state: workflowState };
  }, [projectId, queryClient, workflowState]);

  return query;
}
