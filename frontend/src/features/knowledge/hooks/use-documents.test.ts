import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import {
  useCreateDocument,
  useDeleteDocument,
  useDocument,
  useDocuments,
  useReprocessDocument,
} from "./use-documents";
import { API_ENDPOINTS } from "@/constants/api";

vi.mock("@/lib/api-client", () => ({
  apiCall: vi.fn(),
  apiCallNoContent: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      message: string,
      public code?: string,
    ) {
      super(message);
      this.name = "ApiError";
    }
  },
}));

import { apiCall, apiCallNoContent, ApiError } from "@/lib/api-client";

const mockApiCall = vi.mocked(apiCall);
const mockDelete = vi.mocked(apiCallNoContent);

const MOCK_DOCUMENT = {
  id: "doc-1",
  title: "Architecture Notes",
  status: "completed",
  metadata: { tags: ["architecture"] },
  chunk_count: 2,
  created_at: "2026-04-20T00:00:00Z",
  updated_at: "2026-04-20T00:00:00Z",
  error_message: null,
};

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  });
}

function createWrapper(queryClient = createQueryClient()) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useDocuments", () => {
  it("fetches documents and stores them under the documents query key", async () => {
    mockApiCall.mockResolvedValueOnce({
      items: [MOCK_DOCUMENT],
      total: 1,
      limit: 20,
      offset: 0,
    });
    const queryClient = createQueryClient();
    const { result } = renderHook(() => useDocuments(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.DOCUMENTS,
      expect.anything(),
    );
    expect(result.current.data).toEqual([MOCK_DOCUMENT]);
    expect(queryClient.getQueryData(["documents"])).toEqual([MOCK_DOCUMENT]);
  });
});

describe("useDocument", () => {
  it("fetches one document by id", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_DOCUMENT);
    const queryClient = createQueryClient();
    const { result } = renderHook(() => useDocument("doc-1"), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.DOCUMENT_BY_ID("doc-1"),
      expect.anything(),
    );
    expect(queryClient.getQueryData(["document", "doc-1"])).toEqual(
      MOCK_DOCUMENT,
    );
  });

  it("is disabled without a document id", () => {
    const { result } = renderHook(() => useDocument(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(mockApiCall).not.toHaveBeenCalled();
  });
});

describe("useCreateDocument", () => {
  it("posts document content and invalidates documents", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_DOCUMENT);
    const queryClient = createQueryClient();
    queryClient.setQueryData(
      ["documents"],
      [
        {
          ...MOCK_DOCUMENT,
          id: "doc-old",
          title: "Old document",
        },
      ],
    );
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useCreateDocument(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      title: "Architecture Notes",
      content: "Keep it boring.",
      metadata: { tags: ["architecture"] },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.DOCUMENTS,
      expect.anything(),
      {
        method: "POST",
        body: JSON.stringify({
          title: "Architecture Notes",
          content: "Keep it boring.",
          metadata: { tags: ["architecture"] },
        }),
      },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["documents"],
    });
    expect(queryClient.getQueryData(["document", "doc-1"])).toEqual(
      MOCK_DOCUMENT,
    );
    expect(queryClient.getQueryData(["documents"])).toEqual([
      MOCK_DOCUMENT,
      {
        ...MOCK_DOCUMENT,
        id: "doc-old",
        title: "Old document",
      },
    ]);
  });
});

describe("useDeleteDocument", () => {
  // Scenario: Given a successful DELETE, the mutation resolves without data.
  it("calls the DELETE endpoint for the given id", async () => {
    mockDelete.mockResolvedValueOnce(undefined);
    const queryClient = createQueryClient();
    queryClient.setQueryData(
      ["documents"],
      [
        MOCK_DOCUMENT,
        {
          ...MOCK_DOCUMENT,
          id: "doc-keep",
          title: "Keep document",
        },
      ],
    );
    queryClient.setQueryData(["document", "doc-1"], MOCK_DOCUMENT);
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    const removeQueries = vi.spyOn(queryClient, "removeQueries");
    const { result } = renderHook(() => useDeleteDocument(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate("doc-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockDelete).toHaveBeenCalledWith(
      API_ENDPOINTS.DOCUMENT_BY_ID("doc-1"),
      { method: "DELETE" },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["documents"],
    });
    expect(removeQueries).toHaveBeenCalledWith({
      queryKey: ["document", "doc-1"],
    });
    expect(queryClient.getQueryData(["documents"])).toEqual([
      {
        ...MOCK_DOCUMENT,
        id: "doc-keep",
        title: "Keep document",
      },
    ]);
  });

  // Scenario: Given a server error, the mutation surfaces an ApiError.
  it("propagates ApiError from the api client", async () => {
    mockDelete.mockRejectedValueOnce(new ApiError(403, "forbidden"));
    const { result } = renderHook(() => useDeleteDocument(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("doc-1");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect((result.current.error as ApiError).status).toBe(403);
  });
});

describe("useReprocessDocument", () => {
  it("posts to the reprocess endpoint and invalidates documents", async () => {
    const reprocessedDocument = {
      ...MOCK_DOCUMENT,
      status: "processing",
      updated_at: "2026-04-21T00:00:00Z",
    };
    mockApiCall.mockResolvedValueOnce(reprocessedDocument);
    const queryClient = createQueryClient();
    queryClient.setQueryData(
      ["documents"],
      [
        MOCK_DOCUMENT,
        {
          ...MOCK_DOCUMENT,
          id: "doc-other",
          title: "Other document",
        },
      ],
    );
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useReprocessDocument(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate("doc-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.DOCUMENT_REPROCESS("doc-1"),
      expect.anything(),
      { method: "POST" },
    );
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["documents"],
    });
    expect(queryClient.getQueryData(["document", "doc-1"])).toEqual(
      reprocessedDocument,
    );
    expect(queryClient.getQueryData(["documents"])).toEqual([
      reprocessedDocument,
      {
        ...MOCK_DOCUMENT,
        id: "doc-other",
        title: "Other document",
      },
    ]);
  });
});
