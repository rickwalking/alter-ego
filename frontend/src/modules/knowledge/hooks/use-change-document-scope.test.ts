/**
 * The scope-change mutation of the Knowledge Base.
 * Gherkin: tests/features/knowledge-document-scope-ae0502.feature
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";

import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import type { Document } from "@/schemas/knowledge";
import { useChangeDocumentScope } from "./use-documents";

vi.mock("@/lib/api-client", () => ({
  apiCall: vi.fn(),
  apiCallNoContent: vi.fn(),
}));

import { apiCall } from "@/lib/api-client";

const mockApiCall = vi.mocked(apiCall);

const PERSONAL: Document = {
  id: "doc-1",
  title: "Bio",
  status: "completed",
  scope: "personal",
  is_public: false,
  metadata: {},
  chunk_count: 2,
  created_at: "2026-10-22T00:00:00Z",
  updated_at: "2026-10-22T00:00:00Z",
  error_message: null,
};
const OTHER: Document = { ...PERSONAL, id: "doc-2", title: "Notes" };

function wrapperFor(queryClient: QueryClient) {
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

describe("useChangeDocumentScope", () => {
  /** Scenario: The owner changes a document's scope from its card */
  it("patches the scope and puts the answered document in the list", async () => {
    const moved: Document = { ...PERSONAL, scope: "public", is_public: true };
    mockApiCall.mockResolvedValueOnce(moved);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: Infinity } },
    });
    queryClient.setQueryData(["documents"], [PERSONAL, OTHER]);
    const { result } = renderHook(() => useChangeDocumentScope(), {
      wrapper: wrapperFor(queryClient),
    });

    result.current.mutate({ id: "doc-1", scope: "public" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const [url, , init] = mockApiCall.mock.calls[0]!;
    expect(url).toBe(API_ENDPOINTS.DOCUMENT_SCOPE("doc-1"));
    expect(init).toMatchObject({
      method: HTTP_METHODS.PATCH,
      body: JSON.stringify({ scope: "public" }),
    });
    expect(queryClient.getQueryData(["documents"])).toEqual([moved, OTHER]);
    expect(queryClient.getQueryData(["document", "doc-1"])).toEqual(moved);
  });
});
