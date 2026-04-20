import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { API_ENDPOINTS, DEFAULT_BLOG_LANGUAGE } from "@/constants/api";
import {
  carouselBlogI18nResponseSchema,
  carouselBlogWithDesignResponseSchema,
  carouselDesignResponseSchema,
  carouselProjectListResponseSchema,
  carouselProjectResponseSchema,
  carouselSlideResponseSchema,
} from "@/schemas/carousel";
import { apiCall } from "@/lib/api-client";

/** Fetch a single carousel project by ID. */
export function useCarouselProject(id: string) {
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

/** Fetch all carousel projects with optional status and limit filters. */
export function useCarouselProjects(status?: string, limit?: number) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (limit) params.set("limit", String(limit));
  const url = `${API_ENDPOINTS.CAROUSELS}${params.size ? `?${params}` : ""}`;

  return useQuery({
    queryKey: ["carousels", { status, limit }],
    queryFn: () =>
      apiCall(url, carouselProjectListResponseSchema),
  });
}

/** Fetch completed carousel projects for blog listing. */
export function useBlogPosts(limit?: number) {
  const params = new URLSearchParams({ status: "completed" });
  if (limit) params.set("limit", String(limit));
  const url = `${API_ENDPOINTS.CAROUSELS}?${params}`;

  return useQuery({
    queryKey: ["carousels", { status: "completed", limit }],
    queryFn: () =>
      apiCall(url, carouselProjectListResponseSchema),
  });
}

/** Fetch blog content in a specific language. */
export function useCarouselBlog(id: string, lang: string = DEFAULT_BLOG_LANGUAGE) {
  return useQuery({
    queryKey: ["carousel", id, "blog", lang],
    queryFn: () =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_BLOG_LANG(id, lang),
        carouselBlogI18nResponseSchema
      ),
    enabled: !!id,
  });
}

/** Fetch blog content with design tokens. */
export function useCarouselBlogWithDesign(
  id: string,
  lang: string = DEFAULT_BLOG_LANGUAGE
) {
  return useQuery({
    queryKey: ["carousel", id, "blog", lang, "with-design"],
    queryFn: () =>
      apiCall(
        `${API_ENDPOINTS.CAROUSEL_BLOG_LANG(id, lang)}?include_design=true`,
        carouselBlogWithDesignResponseSchema
      ),
    enabled: !!id,
  });
}

/** Fetch design tokens for a carousel. */
export function useCarouselDesign(id: string) {
  return useQuery({
    queryKey: ["carousel", id, "design"],
    queryFn: () =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_DESIGN(id),
        carouselDesignResponseSchema
      ),
    enabled: !!id,
  });
}

/** Fetch slides for a carousel. */
export function useCarouselSlides(id: string) {
  return useQuery({
    queryKey: ["carousel", id, "slides"],
    queryFn: () =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_SLIDES(id),
        z.array(carouselSlideResponseSchema)
      ),
    enabled: !!id,
  });
}