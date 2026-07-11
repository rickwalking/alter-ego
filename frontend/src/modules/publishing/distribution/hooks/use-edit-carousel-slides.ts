import {
  useMutation,
  useQueryClient,
  type UseMutationResult,
} from "@tanstack/react-query";
import { z } from "zod";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { carouselKeys } from "@/modules/carousel-presentation";
import type { LocalizedSlideReview } from "@/modules/publishing/blog/types-ai";

/**
 * AE-0314: persist reviewer text edits to a COMPLETED carousel's slides without
 * regenerating images. The endpoint writes the edited copy to the projection +
 * checkpoint, marks a server-guaranteed republish, and returns the fresh
 * severity-aware validation report (rendered on a blocking rejection).
 */
const slideEditResponseSchema = z.object({
  project_id: z.string(),
  status: z.string(),
  validation: z
    .object({
      blocking: z.boolean().optional(),
      violations: z.array(z.unknown()).optional(),
    })
    .passthrough(),
  needs_republish: z.boolean().optional(),
  updated_slides: z.array(z.number()).optional(),
});

export type EditCarouselSlidesResponse = z.infer<
  typeof slideEditResponseSchema
>;

export function useEditCarouselSlides(): UseMutationResult<
  EditCarouselSlidesResponse,
  Error,
  { projectId: string; editedSlides: LocalizedSlideReview[] }
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      projectId,
      editedSlides,
    }: {
      projectId: string;
      editedSlides: LocalizedSlideReview[];
    }) =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_SLIDES(projectId),
        slideEditResponseSchema,
        {
          method: HTTP_METHODS.PATCH,
          body: JSON.stringify({ edited_slides: editedSlides }),
        },
      ),
    onSuccess: (_data, { projectId }) => {
      void queryClient.invalidateQueries({
        queryKey: carouselKeys.detail(projectId),
      });
    },
  });
}
