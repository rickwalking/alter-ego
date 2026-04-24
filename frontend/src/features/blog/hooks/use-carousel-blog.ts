import { useQuery } from "@tanstack/react-query";
import {
  carouselBlogOptions,
  carouselBlogWithDesignOptions,
  carouselDesignOptions,
  carouselProjectOptions,
  carouselProjectsOptions,
  carouselSlidesOptions,
} from "@/features/carousel/queries";
import { DEFAULT_BLOG_LANGUAGE } from "@/constants/api";

/** Fetch a single carousel project by ID. */
export function useCarouselProject(id: string) {
  return useQuery(carouselProjectOptions(id));
}

/** Fetch all carousel projects with optional status and limit filters. */
export function useCarouselProjects(status?: string, limit?: number) {
  return useQuery(carouselProjectsOptions(status, limit));
}

/** Fetch completed carousel projects for blog listing. */
export function useBlogPosts(limit?: number) {
  return useQuery(carouselProjectsOptions("completed", limit));
}

/** Fetch blog content in a specific language. */
export function useCarouselBlog(id: string, lang: string = DEFAULT_BLOG_LANGUAGE) {
  return useQuery(carouselBlogOptions(id, lang));
}

/** Fetch blog content with design tokens. */
export function useCarouselBlogWithDesign(
  id: string,
  lang: string = DEFAULT_BLOG_LANGUAGE
) {
  return useQuery(carouselBlogWithDesignOptions(id, lang));
}

/** Fetch design tokens for a carousel. */
export function useCarouselDesign(id: string) {
  return useQuery(carouselDesignOptions(id));
}

/** Fetch slides for a carousel. */
export function useCarouselSlides(id: string) {
  return useQuery(carouselSlidesOptions(id));
}
