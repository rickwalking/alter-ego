import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiCall } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import {
  carouselProjectResponseSchema,
  type CarouselCreateRequest,
  type CarouselProjectResponse,
} from "@/schemas/carousel";
import {
  carouselKeys,
  carouselProjectOptions,
} from "@/modules/carousel-presentation";

/** Create a new carousel project and return the created project. */
export function useCreateCarousel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      data: CarouselCreateRequest,
    ): Promise<CarouselProjectResponse> => {
      return apiCall(API_ENDPOINTS.CAROUSELS, carouselProjectResponseSchema, {
        method: HTTP_METHODS.POST,
        body: JSON.stringify(data),
      });
    },
    onSuccess: (project) => {
      queryClient.setQueryData(carouselKeys.detail(project.id), project);
      queryClient.setQueryData<CarouselProjectResponse[]>(
        carouselKeys.list(),
        (previous) =>
          previous
            ? [project, ...previous.filter((item) => item.id !== project.id)]
            : previous,
      );
      queryClient.invalidateQueries({ queryKey: carouselKeys.list() });
    },
    onError: (error) => {
      console.error("Failed to create carousel:", error);
    },
  });
}

/** Fetch carousel project by ID for workspace page. */
export function useCarouselProject(id: string | null) {
  return useQuery(carouselProjectOptions(id));
}

/** Delete a carousel project and invalidate related caches. */
export function useDeleteCarousel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string): Promise<void> => {
      await apiCall(API_ENDPOINTS.CAROUSEL_BY_ID(projectId), z.object({}), {
        method: HTTP_METHODS.DELETE,
      });
    },
    onSuccess: (_data, projectId) => {
      queryClient.removeQueries({ queryKey: carouselKeys.detail(projectId) });
      queryClient.invalidateQueries({ queryKey: carouselKeys.list() });
    },
    onError: (error) => {
      console.error("Failed to delete carousel:", error);
    },
  });
}
