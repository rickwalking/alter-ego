"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS } from "@/constants/api";
import { carouselKeys } from "@/features/carousel/queries";

const instagramPublishResponseSchema = z.object({
  status: z.enum(["queued", "published", "failed"]),
  ig_post_id: z.string().nullable().optional(),
  error_message: z.string().nullable().optional(),
});

export type InstagramPublishResponse = z.infer<
  typeof instagramPublishResponseSchema
>;

interface InstagramPublishPayload {
  projectId: string;
  caption: string;
}

export function usePublishInstagram() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      projectId,
      caption,
    }: InstagramPublishPayload): Promise<InstagramPublishResponse> => {
      return apiCall(
        API_ENDPOINTS.CAROUSEL_PUBLISH_INSTAGRAM(projectId),
        instagramPublishResponseSchema,
        {
          method: "POST",
          body: JSON.stringify({ caption }),
        },
      );
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: carouselKeys.detail(variables.projectId),
      });
    },
    onError: (error) => {
      console.error("Failed to publish to Instagram:", error);
    },
  });
}
