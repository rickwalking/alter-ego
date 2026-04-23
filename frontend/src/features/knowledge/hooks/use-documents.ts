import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiCall, apiCallNoContent } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import {
  documentSchema,
  documentListResponseSchema,
  type Document,
  type DocumentListResponse,
  type CreateDocumentRequest,
} from "@/schemas/knowledge";

const DOCUMENTS_KEY = "documents";
const DOCUMENT_KEY = "document";

export function useDocuments() {
  return useQuery({
    queryKey: [DOCUMENTS_KEY],
    queryFn: async () => {
      const result = await apiCall<DocumentListResponse>(
        API_ENDPOINTS.DOCUMENTS,
        documentListResponseSchema
      );
      return result.items;
    },
  });
}

export function useDocument(id: string | null) {
  return useQuery({
    queryKey: [DOCUMENT_KEY, id],
    queryFn: async () => {
      return apiCall<Document>(
        API_ENDPOINTS.DOCUMENT_BY_ID(id as string),
        documentSchema
      );
    },
    enabled: !!id,
  });
}

export function useCreateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateDocumentRequest) => {
      return apiCall<Document>(API_ENDPOINTS.DOCUMENTS, documentSchema, {
        method: HTTP_METHODS.POST,
        body: JSON.stringify(data),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [DOCUMENTS_KEY] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiCallNoContent(API_ENDPOINTS.DOCUMENT_BY_ID(id), {
        method: HTTP_METHODS.DELETE,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [DOCUMENTS_KEY] });
    },
  });
}

export function useReprocessDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return apiCall<Document>(
        API_ENDPOINTS.DOCUMENT_REPROCESS(id),
        documentSchema,
        { method: HTTP_METHODS.POST }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [DOCUMENTS_KEY] });
    },
  });
}
