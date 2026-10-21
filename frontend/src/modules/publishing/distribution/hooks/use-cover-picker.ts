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
import { carouselKeys } from "@/modules/carousel-presentation";
import type { CoverPickInput } from "./types";

/**
 * The slide-1 cover picker of a Ponto de Vista carousel on the
 * publish step. The options are the owner's library photos and, when the
 * autopilot run has one, the GrokBot cover offer; a pick re-renders the
 * slides + PDFs server-side and returns the fresh artifact version.
 */
const coverOptionSchema = z.object({
  asset_id: z.string(),
  source: z.enum(["library", "offer"]),
  kind: z.string().optional(),
});

const coverOptionsSchema = z.object({
  project_id: z.string(),
  current_asset_id: z.string().nullable(),
  options: z.array(coverOptionSchema),
});

/**
 * The CAS version is read right before the PUT, never from page state (the
 * workflow SSE merge dropped `lock_version`, and a successful switch bumps it).
 */
const workflowVersionSchema = z.object({ lock_version: z.number() });

const coverPickResponseSchema = z.object({
  project_id: z.string(),
  status: z.string(),
  current_asset_id: z.string().nullable(),
  artifact_version: z.string().nullable().optional(),
});

export type CoverOptions = z.infer<typeof coverOptionsSchema>;
export type CoverPickResponse = z.infer<typeof coverPickResponseSchema>;

export const coverOptionKeys = {
  detail: (projectId: string) => ["carousel-cover-options", projectId] as const,
};

export function useCoverOptions(
  projectId: string,
): UseQueryResult<CoverOptions> {
  return useQuery({
    queryKey: coverOptionKeys.detail(projectId),
    queryFn: () =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_COVER_OPTIONS(projectId),
        coverOptionsSchema,
      ),
  });
}

export function usePickCover(): UseMutationResult<
  CoverPickResponse,
  Error,
  CoverPickInput
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ projectId, assetId }: CoverPickInput) => {
      const { lock_version: expectedVersion } = await apiCall(
        API_ENDPOINTS.CAROUSEL_WORKFLOW_STATE(projectId),
        workflowVersionSchema,
      );
      return apiCall(
        API_ENDPOINTS.CAROUSEL_COVER(projectId),
        coverPickResponseSchema,
        {
          method: HTTP_METHODS.PUT,
          body: JSON.stringify({
            asset_id: assetId,
            expected_version: expectedVersion,
          }),
        },
      );
    },
    onSuccess: (_data, { projectId }) => {
      void queryClient.invalidateQueries({
        queryKey: coverOptionKeys.detail(projectId),
      });
      void queryClient.invalidateQueries({
        queryKey: carouselKeys.detail(projectId),
      });
    },
  });
}
