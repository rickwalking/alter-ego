import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS } from "@/constants/api";
import { STATUS_POLL_INTERVAL } from "@/constants/create";
import {
  carouselProjectResponseSchema,
  carouselStatusResponseSchema,
  type CarouselProjectResponse,
  type CarouselStatusResponse,
  type CarouselCreateRequest,
} from "@/schemas/carousel";

const CAROUSELS_KEY = "carousels";

type GenerateArgs = {
  projectId: string;
  sources?: string[];
};

/** Create a new carousel project and return the created project. */
export function useCreateCarousel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CarouselCreateRequest): Promise<CarouselProjectResponse> => {
      return apiCall(
        API_ENDPOINTS.CAROUSELS,
        carouselProjectResponseSchema,
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CAROUSELS_KEY] });
    },
  });
}

/** Trigger the backend pipeline for an existing project. Long-running. */
export function useGenerateCarousel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ projectId, sources }: GenerateArgs): Promise<CarouselStatusResponse> => {
      return apiCall(
        API_ENDPOINTS.CAROUSEL_GENERATE(projectId),
        carouselStatusResponseSchema,
        {
          method: "POST",
          body: JSON.stringify({ sources: sources ?? null }),
        }
      );
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["carousel-status", variables.projectId] });
      queryClient.invalidateQueries({ queryKey: ["carousel", variables.projectId] });
    },
  });
}

/** Poll carousel generation status by ID. */
export function useCarouselStatus(id: string | null) {
  return useQuery({
    queryKey: ["carousel-status", id],
    queryFn: () =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_STATUS(id as string),
        carouselStatusResponseSchema
      ),
    enabled: !!id,
    refetchInterval: STATUS_POLL_INTERVAL,
  });
}

/** Fetch carousel project by ID for workspace page. */
export function useCarouselProject(id: string | null) {
  return useQuery({
    queryKey: ["carousel", id],
    queryFn: () =>
      apiCall(
        API_ENDPOINTS.CAROUSELS + `/${id}`,
        carouselProjectResponseSchema
      ),
    enabled: !!id,
  });
}
