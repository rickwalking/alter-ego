import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiCall } from "@/lib/api-client";
import {
  documentSchema,
  documentListResponseSchema,
  type Document,
  type DocumentListResponse,
  type CreateDocumentRequest,
} from "@/schemas/knowledge";

const DOCUMENTS_KEY = "documents";

export function useDocuments() {
  return useQuery({
    queryKey: [DOCUMENTS_KEY],
    queryFn: async () => {
      const result = await apiCall<DocumentListResponse>(
        "/api/documents",
        documentListResponseSchema
      );
      return result.items;
    },
  });
}

export function useDocument(id: string | null) {
  return useQuery({
    queryKey: ["document", id],
    queryFn: async () => {
      return apiCall<Document>(
        `/api/documents/${id}`,
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
      return apiCall<Document>("/api/documents", documentSchema, {
        method: "POST",
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
      await fetch(`/api/documents/${id}`, { method: "DELETE" });
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
        `/api/documents/${id}/reprocess`,
        documentSchema,
        { method: "POST" }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [DOCUMENTS_KEY] });
    },
  });
}
