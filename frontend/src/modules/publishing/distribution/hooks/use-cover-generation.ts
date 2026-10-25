import { useEffect, useRef } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import {
  GENERATION_STATUS,
  coverGenerationSchema,
  coverGenerationsSchema,
  type CoverGeneration,
  type CoverGenerations,
} from "./cover-generation-schema";
import type { CoverGenerationInput } from "./types";
import { coverOptionKeys } from "./use-cover-picker";

export type { CoverGenerationInput } from "./types";
export {
  GENERATION_STATUS,
  type CoverGeneration,
  type CoverGenerations,
} from "./cover-generation-schema";

/**
 * Grok covers generated from the owner's library photos on the publish step.
 * The list carries the caps in use; it is polled while a generation runs, and
 * the cover options are refreshed when one settles.
 */
const POLL_INTERVAL_MS = 4000;

export const coverGenerationKeys = {
  detail: (projectId: string) =>
    ["carousel-cover-generations", projectId] as const,
};

function hasPending(data: CoverGenerations | undefined): boolean {
  return (
    data?.generations.some((g) => g.status === GENERATION_STATUS.PENDING) ??
    false
  );
}

function newestSucceeded(data: CoverGenerations | undefined): string | null {
  return (
    data?.generations.find((g) => g.status === GENERATION_STATUS.SUCCEEDED)
      ?.id ?? null
  );
}

/**
 * The generations, polled only while one is pending. The cover
 * options refresh whenever the newest succeeded generation changes, so a fast
 * job or one that finished while polling was paused still shows up.
 */
export function useCoverGenerations(
  projectId: string,
): UseQueryResult<CoverGenerations> {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: coverGenerationKeys.detail(projectId),
    queryFn: () =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_COVER_GENERATIONS(projectId),
        coverGenerationsSchema,
      ),
    retry: false,
    refetchInterval: (current) =>
      hasPending(current.state.data) ? POLL_INTERVAL_MS : false,
  });
  const loaded = query.data !== undefined;
  const newest = newestSucceeded(query.data);
  const seen = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    if (!loaded) {
      return;
    }
    if (seen.current !== undefined && seen.current !== newest) {
      void queryClient.invalidateQueries({
        queryKey: coverOptionKeys.detail(projectId),
      });
    }
    seen.current = newest;
  }, [loaded, newest, projectId, queryClient]);
  return query;
}

/** Start one confirmed generation; the list refetches and starts polling. */
export function useStartCoverGeneration(): UseMutationResult<
  CoverGeneration,
  Error,
  CoverGenerationInput
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, photoIds, prompt }: CoverGenerationInput) =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_COVER_GENERATIONS(projectId),
        coverGenerationSchema,
        {
          method: HTTP_METHODS.POST,
          body: JSON.stringify({
            photo_ids: photoIds,
            prompt,
            confirmed: true,
          }),
        },
      ),
    onSuccess: (_data, { projectId }) => {
      void queryClient.invalidateQueries({
        queryKey: coverGenerationKeys.detail(projectId),
      });
    },
  });
}
