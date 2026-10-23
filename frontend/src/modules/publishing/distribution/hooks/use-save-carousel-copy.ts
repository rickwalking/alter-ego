import {
  useMutation,
  useQueryClient,
  type UseMutationResult,
} from "@tanstack/react-query";
import { z } from "zod";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { HTTP_HEADER_IF_MATCH } from "@/constants/workflow";
import { carouselKeys } from "@/modules/carousel-presentation";
import type { CarouselCopySaveInput } from "./types";

/**
 * Save the Instagram caption and the PT/EN LinkedIn posts of a carousel. The
 * request carries the loaded ``lock_version`` as ``If-Match``; the response
 * returns the saved texts and the version the next save must send.
 */
export const carouselCopyResponseSchema = z.object({
  project_id: z.string(),
  caption: z.string().nullable(),
  linkedin_post_pt: z.string().nullable(),
  linkedin_post_en: z.string().nullable(),
  lock_version: z.number(),
});

export type CarouselCopyResponse = z.infer<typeof carouselCopyResponseSchema>;

export function useSaveCarouselCopy(): UseMutationResult<
  CarouselCopyResponse,
  Error,
  CarouselCopySaveInput
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, lockVersion, texts }: CarouselCopySaveInput) =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_COPY(projectId),
        carouselCopyResponseSchema,
        {
          method: HTTP_METHODS.PATCH,
          headers: { [HTTP_HEADER_IF_MATCH]: String(lockVersion) },
          body: JSON.stringify(texts),
        },
      ),
    onSuccess: (_data, { projectId }) => {
      void queryClient.invalidateQueries({
        queryKey: carouselKeys.detail(projectId),
      });
    },
  });
}
