import { useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { carouselKeys } from "@/modules/carousel-presentation";

/** AE-0375: response of `PUT /api/carousels/{id}/hook`. */
const saveHookResponseSchema = z.object({
  project_id: z.string(),
  hook_text: z.string(),
});

export type SaveHookResponse = z.infer<typeof saveHookResponseSchema>;

export interface SaveHookInput {
  projectId: string;
  hookText: string;
}

/**
 * AE-0375: store the owner's slide-1 hook (≤60 characters, ≤10 words). The
 * content phase drafts slide 1 with it.
 */
export function useSaveCarouselHook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      projectId,
      hookText,
    }: SaveHookInput): Promise<SaveHookResponse> =>
      apiCall(API_ENDPOINTS.CAROUSEL_HOOK(projectId), saveHookResponseSchema, {
        method: HTTP_METHODS.PUT,
        body: JSON.stringify({ hook_text: hookText }),
      }),
    onSuccess: (_data, { projectId }) => {
      void queryClient.invalidateQueries({
        queryKey: carouselKeys.detail(projectId),
      });
    },
  });
}
