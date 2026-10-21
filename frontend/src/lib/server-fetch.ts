import { z } from "zod";
import {
  API_ENDPOINTS,
  DEFAULT_BACKEND_URL,
  PRODUCTION_BACKEND_URL,
} from "@/constants/api";
import { SERVER_FETCH } from "@/constants/server-fetch";
import {
  carouselDesignResponseSchema,
  carouselProjectListResponseSchema,
  carouselPublicResponseSchema,
} from "@/schemas/carousel";
import {
  publicBlogPostListResponseSchema,
  publicBlogPostResponseSchema,
} from "@/schemas/public-blog-post";

/**
 * API base URL. Server-side (Docker) ``API_BASE_URL`` overrides the internal
 * hostname fallback; exported for the prod-reachability test.
 */
export function getBaseUrl(): string {
  if (typeof window === "undefined" && process.env.API_BASE_URL) {
    return process.env.API_BASE_URL;
  }
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (typeof window === "undefined" && envUrl?.startsWith("/")) {
    return PRODUCTION_BACKEND_URL;
  }
  return envUrl !== undefined && envUrl !== "" ? envUrl : DEFAULT_BACKEND_URL;
}

interface ServerFetchOptions {
  revalidate?: number;
  cache?: RequestInit["cache"];
}

/** `cache` wins; otherwise ISR via `next.revalidate`; otherwise defaults. */
function toFetchInit(
  options?: ServerFetchOptions,
): RequestInit & { next?: { revalidate?: number } } {
  if (options?.cache) {
    return { cache: options.cache };
  }
  if (options?.revalidate) {
    return { next: { revalidate: options.revalidate } };
  }
  return {};
}

/** Parse an OK response against the schema; null (logged) on a contract break. */
async function parseValidated<T>(
  res: Response,
  schema: z.ZodSchema<T>,
): Promise<T | null> {
  const json: unknown = await res.json();
  const result = schema.safeParse(json);
  if (!result.success) {
    console.error("Server fetch validation failed:", result.error.issues);
    return null;
  }
  return result.data;
}

/** Server-side fetch: null on network error, non-OK status or invalid data. */
async function validatedFetch<T>(
  url: string,
  schema: z.ZodSchema<T>,
  options?: ServerFetchOptions,
): Promise<T | null> {
  try {
    const res = await fetch(`${getBaseUrl()}${url}`, toFetchInit(options));
    return res.ok ? await parseValidated(res, schema) : null;
  } catch {
    return null;
  }
}

export async function fetchCompletedProjects(
  limit: number = SERVER_FETCH.DEFAULT_PROJECT_LIMIT,
): Promise<z.infer<typeof carouselProjectListResponseSchema>> {
  const result = await validatedFetch(
    `${API_ENDPOINTS.CAROUSELS}?public=true&status=${SERVER_FETCH.COMPLETED_STATUS}&limit=${limit}`,
    carouselProjectListResponseSchema,
    { cache: "no-store" },
  );

  return result ?? { items: [], total: 0, limit, offset: 0 };
}

/**
 * Carousel design tokens for theming a carousel-origin blog post.
 *
 * Theme only (colors/typography/layout): the public blog never reads article
 * text from the carousel `/blog` endpoint, and the caller drops `images`.
 */
export async function fetchCarouselDesign(
  id: string,
  lang = "pt",
): Promise<z.infer<typeof carouselDesignResponseSchema> | null> {
  return validatedFetch(
    API_ENDPOINTS.CAROUSEL_DESIGN(id, lang),
    carouselDesignResponseSchema,
    { cache: "no-store" },
  );
}

/**
 * Published carousel gallery page. Newest-first by creation date;
 * a failed/empty feed returns an empty page instead of throwing.
 */
export async function fetchPublicCarousels(
  limit: number = SERVER_FETCH.PUBLIC_CAROUSEL_PAGE_SIZE,
  offset = 0,
): Promise<z.infer<typeof carouselProjectListResponseSchema>> {
  const result = await validatedFetch(
    `${API_ENDPOINTS.CAROUSELS}?public=true&status=${SERVER_FETCH.COMPLETED_STATUS}&sort=created_at&limit=${limit}&offset=${offset}`,
    carouselProjectListResponseSchema,
    { cache: "no-store" },
  );

  return result ?? { items: [], total: 0, limit, offset };
}

/** One published carousel's lean public viewer projection. */
export async function fetchPublicCarousel(
  id: string,
): Promise<z.infer<typeof carouselPublicResponseSchema> | null> {
  return validatedFetch(
    API_ENDPOINTS.CAROUSEL_PUBLIC(id),
    carouselPublicResponseSchema,
    {
      cache: "no-store",
    },
  );
}

export async function fetchPublicBlogPosts(
  limit: number = SERVER_FETCH.DEFAULT_PROJECT_LIMIT,
): Promise<z.infer<typeof publicBlogPostListResponseSchema> | null> {
  return validatedFetch(
    `${API_ENDPOINTS.PUBLIC_BLOG_POSTS}?limit=${limit}`,
    publicBlogPostListResponseSchema,
    { cache: "no-store" },
  );
}

export async function fetchPublicBlogPost(
  id: string,
): Promise<z.infer<typeof publicBlogPostResponseSchema> | null> {
  return validatedFetch(
    API_ENDPOINTS.PUBLIC_BLOG_POST_BY_ID(id),
    publicBlogPostResponseSchema,
    { cache: "no-store" },
  );
}
