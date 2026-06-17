import {
  useQuery,
  useSuspenseQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { apiCall, apiCallNoContent } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import {
  documentSchema,
  type Document,
  type CreateDocumentRequest,
} from "@/schemas/knowledge";
import {
  documentKeys,
  documentOptions,
  documentsOptions,
} from "@/modules/knowledge/queries";

/**
 * Suspense-oriented document list read (ADR-010). Suspends until data resolves
 * and throws on error, so the consumer pairs it with a `<Suspense>` boundary
 * (loading) and the route-level `error.tsx` boundary (error). `data` is always
 * defined — no `isLoading` branch in the consumer.
 */
export function useDocuments() {
  return useSuspenseQuery(documentsOptions());
}

export function useDocument(id: string | null) {
  return useQuery(documentOptions(id));
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
    onSuccess: (document) => {
      queryClient.setQueryData(documentKeys.detail(document.id), document);
      queryClient.setQueryData<Document[]>(documentKeys.list(), (previous) =>
        previous
          ? [document, ...previous.filter((item) => item.id !== document.id)]
          : previous,
      );
      queryClient.invalidateQueries({ queryKey: documentKeys.list() });
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
    onSuccess: (_, id) => {
      queryClient.setQueryData<Document[]>(documentKeys.list(), (previous) =>
        previous?.filter((document) => document.id !== id),
      );
      queryClient.removeQueries({ queryKey: documentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: documentKeys.list() });
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
        { method: HTTP_METHODS.POST },
      );
    },
    onSuccess: (document) => {
      queryClient.setQueryData(documentKeys.detail(document.id), document);
      queryClient.setQueryData<Document[]>(documentKeys.list(), (previous) =>
        previous?.map((item) => (item.id === document.id ? document : item)),
      );
      queryClient.invalidateQueries({ queryKey: documentKeys.list() });
    },
  });
}
