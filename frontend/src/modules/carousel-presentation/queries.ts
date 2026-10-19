import { queryOptions, skipToken } from "@tanstack/react-query";
import { API_ENDPOINTS } from "@/constants/api";
import { apiCall } from "@/lib/api-client";
import {
  carouselProjectListResponseSchema,
  carouselProjectResponseSchema,
  type CarouselProjectListResponse,
  type CarouselProjectResponse,
} from "@/schemas/carousel";

type CarouselListFilters = {
  status?: string;
  limit?: number;
};

export const carouselKeys = {
  list: (filters?: CarouselListFilters) =>
    filters ? (["carousels", filters] as const) : (["carousels"] as const),
  detail: (id: string | null) => ["carousel", id] as const,
  slides: (id: string | null) => ["carousel", id, "slides"] as const,
};

function buildCarouselListUrl(filters: CarouselListFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.limit) params.set("limit", String(filters.limit));
  return `${API_ENDPOINTS.CAROUSELS}${params.size ? `?${params}` : ""}`;
}

export function carouselListOptions(filters: CarouselListFilters = {}) {
  const normalizedFilters = {
    status: filters.status,
    limit: filters.limit,
  };

  return queryOptions({
    queryKey: carouselKeys.list(normalizedFilters),
    queryFn: () =>
      apiCall<CarouselProjectListResponse>(
        buildCarouselListUrl(normalizedFilters),
        carouselProjectListResponseSchema,
      ),
  });
}

export function carouselProjectOptions(id: string | null) {
  return queryOptions({
    queryKey: carouselKeys.detail(id),
    queryFn: id
      ? () =>
          apiCall<CarouselProjectResponse>(
            API_ENDPOINTS.CAROUSEL_BY_ID(id),
            carouselProjectResponseSchema,
          )
      : skipToken,
  });
}
