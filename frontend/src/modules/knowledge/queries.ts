import { queryOptions, skipToken } from "@tanstack/react-query";
import { API_ENDPOINTS } from "@/constants/api";
import { apiCall } from "@/lib/api-client";
import {
  documentListResponseSchema,
  documentSchema,
  type Document,
  type DocumentListResponse,
} from "@/schemas/knowledge";

export const documentKeys = {
  list: () => ["documents"] as const,
  detail: (id: string | null) => ["document", id] as const,
};

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
