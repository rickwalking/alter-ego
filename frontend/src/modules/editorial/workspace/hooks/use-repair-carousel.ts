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
 * AE-0311: run the bounded deterministic repair pipeline (scaffold strip,
 * heading-echo removal, body trim, canonical shape normalization, policy-gated
 * casing) over a carousel's localized slides. Idempotent — a second call on
 * already-clean content is a no-op.
 */
const repairSlideDiffSchema = z.object({
  slide_index: z.number().nullable().optional(),
  locale: z.string().nullable().optional(),
  repaired: z.boolean(),
  repaired_codes: z.array(z.string()),
  remaining_codes: z.array(z.string()),
});

const repairViolationSchema = z.object({
  code: z.string(),
  message: z.string(),
  slide_index: z.number().nullable().optional(),
  locale: z.string().nullable().optional(),
  field: z.string().nullable().optional(),
  severity: z.string().optional(),
});

const repairValidationSchema = z.object({
  validation_status: z.string(),
  validated_at: z.string(),
  blocking: z.boolean(),
  violations: z.array(repairViolationSchema),
});

const repairResponseSchema = z.object({
  project_id: z.string(),
  status: z.string(),
  repaired: z.array(repairSlideDiffSchema),
  validation: repairValidationSchema,
  needs_republish: z.boolean(),
});

export type RepairSlideDiff = z.infer<typeof repairSlideDiffSchema>;
export type RepairCarouselResponse = z.infer<typeof repairResponseSchema>;

export function useRepairCarousel(): UseMutationResult<
  RepairCarouselResponse,
  Error,
  { projectId: string }
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ projectId }: { projectId: string }) => {
      return apiCall(
        API_ENDPOINTS.CAROUSEL_REPAIR(projectId),
        repairResponseSchema,
        { method: HTTP_METHODS.POST },
      );
    },
    onSuccess: (_data, { projectId }) => {
      void queryClient.invalidateQueries({
        queryKey: carouselKeys.slides(projectId),
      });
    },
  });
}
