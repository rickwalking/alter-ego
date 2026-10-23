import { queryOptions, skipToken } from "@tanstack/react-query";
import { API_ENDPOINTS } from "@/constants/api";
import { apiCall } from "@/lib/api-client";
import { CAROUSEL_SOURCES_PAGE_SIZE } from "@/constants/knowledge-sources";
import {
  carouselSourceListResponseSchema,
  type CarouselSourceListResponse,
  documentListResponseSchema,
  documentSchema,
  type Document,
  type DocumentListResponse,
} from "@/schemas/knowledge";

export const documentKeys = {
  list: () => ["documents"] as const,
  detail: (id: string | null) => ["document", id] as const,
};

export const carouselSourceKeys = {
  page: (offset: number, projectId: string) =>
    ["knowledge", "carousel-sources", offset, projectId] as const,
};

/** The listing URL of one page of carousel sources. */
export function carouselSourcesUrl(offset: number, projectId: string): string {
  const params = new URLSearchParams({
    limit: String(CAROUSEL_SOURCES_PAGE_SIZE),
    offset: String(offset),
  });
  if (projectId) params.set("project_id", projectId);
  return `${API_ENDPOINTS.KNOWLEDGE_CAROUSEL_SOURCES}?${params.toString()}`;
}

/** One page of the caller's carousel sources, optionally of one carousel. */
export function carouselSourcesOptions(offset: number, projectId: string) {
  return queryOptions({
    queryKey: carouselSourceKeys.page(offset, projectId),
    queryFn: () =>
      apiCall<CarouselSourceListResponse>(
        carouselSourcesUrl(offset, projectId),
        carouselSourceListResponseSchema,
      ),
  });
}

export function documentsOptions() {
  return queryOptions({
    queryKey: documentKeys.list(),
    queryFn: async () => {
      const result = await apiCall<DocumentListResponse>(
        API_ENDPOINTS.DOCUMENTS,
        documentListResponseSchema,
      );
      return result.items;
    },
  });
}

export function documentOptions(id: string | null) {
  return queryOptions({
    queryKey: documentKeys.detail(id),
    queryFn: id
      ? () =>
          apiCall<Document>(API_ENDPOINTS.DOCUMENT_BY_ID(id), documentSchema)
      : skipToken,
  });
}
