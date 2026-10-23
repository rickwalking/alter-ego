import { useEffect, useRef } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import { z } from "zod";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import type { CoverGenerationInput } from "./types";
import { coverOptionKeys } from "./use-cover-picker";

export type { CoverGenerationInput } from "./types";

/**
 * Grok covers generated from the owner's library photos on the publish step.
 * The list carries the caps in use; it is polled while a generation runs, and
 * the cover options are refreshed when one settles.
 */
const POLL_INTERVAL_MS = 4000;

export const GENERATION_STATUS = {
  PENDING: "pending",
  SUCCEEDED: "succeeded",
  FAILED: "failed",
} as const;

const coverGenerationSchema = z.object({
  id: z.string(),
  status: z.enum([
    GENERATION_STATUS.PENDING,
    GENERATION_STATUS.SUCCEEDED,
    GENERATION_STATUS.FAILED,
  ]),
  error_code: z.string().nullable().optional(),
  asset_id: z.string().nullable().optional(),
  created_at: z.string(),
  completed_at: z.string().nullable().optional(),
});

const coverGenerationsSchema = z.object({
  carousel_used: z.number(),
  carousel_cap: z.number(),
  month_used: z.number(),
  month_cap: z.number(),
  generations: z.array(coverGenerationSchema),
});

export type CoverGeneration = z.infer<typeof coverGenerationSchema>;
export type CoverGenerations = z.infer<typeof coverGenerationsSchema>;

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

/** The generations, polled while one runs; the cover options refresh when it settles. */
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
    refetchInterval: (current) =>
      hasPending(current.state.data) ? POLL_INTERVAL_MS : false,
  });
  const running = hasPending(query.data);
  const wasRunning = useRef(running);
  useEffect(() => {
    if (wasRunning.current && !running) {
      void queryClient.invalidateQueries({
        queryKey: coverOptionKeys.detail(projectId),
      });
    }
    wasRunning.current = running;
  }, [running, projectId, queryClient]);
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
