"use client";

import { useQuery } from "@tanstack/react-query";

import { API_ENDPOINTS, ROUTE_PATHS } from "@/constants/api";
import { apiCall } from "@/lib/api-client";
import { publicBlogPostListResponseSchema } from "@/schemas/public-blog-post";
import type { CarouselPublicPostHref } from "./types";

const CAROUSEL_BLOG_POST_QUERY_KEY = "public-blog-post-for-carousel";

/**
 * The public blog post made from carousel `projectId`, read from the public
 * (published-only) list, so a link built from it never opens a 404 page.
 */
export function useCarouselPublicPostHref(
  projectId: string,
): CarouselPublicPostHref {
  const query = useQuery({
    queryKey: [CAROUSEL_BLOG_POST_QUERY_KEY, projectId],
    queryFn: () =>
      apiCall(
        API_ENDPOINTS.PUBLIC_BLOG_POST_FOR_CAROUSEL(projectId),
        publicBlogPostListResponseSchema,
      ),
    select: (list) => list.items[0]?.id ?? null,
  });
  return {
    href: query.data ? ROUTE_PATHS.BLOG_POST(query.data) : null,
    refetch: query.refetch,
  };
}
