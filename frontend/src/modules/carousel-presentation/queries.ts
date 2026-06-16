import { queryOptions, skipToken } from "@tanstack/react-query";
import { z } from "zod";
import { API_ENDPOINTS, DEFAULT_BLOG_LANGUAGE } from "@/constants/api";
import { MS_PER_MINUTE } from "@/constants/time";
import { apiCall } from "@/lib/api-client";
import {
  carouselBlogI18nResponseSchema,
  carouselBlogWithDesignResponseSchema,
  carouselDesignResponseSchema,
  carouselProjectListResponseSchema,
  carouselProjectResponseSchema,
  carouselSlideResponseSchema,
  type CarouselProjectListResponse,
  type CarouselProjectResponse,
} from "@/schemas/carousel";

/** Stale time for published carousel content (rarely changes once exported). */
const CAROUSEL_STALE_TIME_MINUTES = 15;
const CAROUSEL_STALE_TIME_MS = MS_PER_MINUTE * CAROUSEL_STALE_TIME_MINUTES;

type CarouselListFilters = {
  status?: string;
  limit?: number;
};

export const carouselKeys = {
  list: (filters?: CarouselListFilters) =>
    filters ? (["carousels", filters] as const) : (["carousels"] as const),
  detail: (id: string | null) => ["carousel", id] as const,
  blog: (id: string | null, lang: string = DEFAULT_BLOG_LANGUAGE) =>
    ["carousel", id, "blog", lang] as const,
  blogWithDesign: (id: string | null, lang: string = DEFAULT_BLOG_LANGUAGE) =>
    ["carousel", id, "blog", lang, "with-design"] as const,
  design: (id: string | null) => ["carousel", id, "design"] as const,
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

export function carouselProjectsOptions(status?: string, limit?: number) {
  return carouselListOptions({ status, limit });
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

export function carouselBlogOptions(
  id: string | null,
  lang: string = DEFAULT_BLOG_LANGUAGE,
) {
  return queryOptions({
    queryKey: carouselKeys.blog(id, lang),
    queryFn: id
      ? () =>
          apiCall(
            API_ENDPOINTS.CAROUSEL_BLOG_LANG(id, lang),
            carouselBlogI18nResponseSchema,
          )
      : skipToken,
    staleTime: CAROUSEL_STALE_TIME_MS,
  });
}

export function carouselBlogWithDesignOptions(
  id: string | null,
  lang: string = DEFAULT_BLOG_LANGUAGE,
) {
  return queryOptions({
    queryKey: carouselKeys.blogWithDesign(id, lang),
    queryFn: id
      ? () =>
          apiCall(
            `${API_ENDPOINTS.CAROUSEL_BLOG_LANG(id, lang)}?include_design=true`,
            carouselBlogWithDesignResponseSchema,
          )
      : skipToken,
    staleTime: CAROUSEL_STALE_TIME_MS,
  });
}

export function carouselDesignOptions(id: string | null) {
  return queryOptions({
    queryKey: carouselKeys.design(id),
    queryFn: id
      ? () =>
          apiCall(
            API_ENDPOINTS.CAROUSEL_DESIGN(id),
            carouselDesignResponseSchema,
          )
      : skipToken,
    staleTime: CAROUSEL_STALE_TIME_MS,
  });
}

export function carouselSlidesOptions(id: string | null) {
  return queryOptions({
    queryKey: carouselKeys.slides(id),
    queryFn: id
      ? () =>
          apiCall(
            API_ENDPOINTS.CAROUSEL_SLIDES(id),
            z.array(carouselSlideResponseSchema),
          )
      : skipToken,
    staleTime: CAROUSEL_STALE_TIME_MS,
  });
}
