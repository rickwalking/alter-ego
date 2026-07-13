import {
  useMutation,
  useQueryClient,
  type UseMutationResult,
} from "@tanstack/react-query";
import { z } from "zod";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { carouselKeys } from "@/modules/carousel-presentation";

/**
 * AE-0313: rebuild + re-activate a completed carousel's PDF/slide artifacts
 * from the persisted slide data. Idempotent — safe to click twice (unchanged
 * content re-activates the same version).
 */
const republishResponseSchema = z.object({
  project_id: z.string(),
  status: z.string(),
  artifact_version: z.string().nullable().optional(),
  pdf_path: z.string().nullable().optional(),
  pdf_path_en: z.string().nullable().optional(),
});

export type RepublishCarouselResponse = z.infer<typeof republishResponseSchema>;

export function useRepublishCarousel(): UseMutationResult<
  RepublishCarouselResponse,
  Error,
  { projectId: string }
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ projectId }: { projectId: string }) => {
      return apiCall(
        API_ENDPOINTS.CAROUSEL_REPUBLISH(projectId),
        republishResponseSchema,
        { method: HTTP_METHODS.POST },
      );
    },
    onSuccess: (_data, { projectId }) => {
      void queryClient.invalidateQueries({
        queryKey: carouselKeys.detail(projectId),
      });
    },
  });
}
