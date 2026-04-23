import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { useDeleteDocument } from "./use-documents";
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

import { apiCallNoContent, ApiError } from "@/lib/api-client";

const mockDelete = vi.mocked(apiCallNoContent);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useDeleteDocument", () => {
  // Scenario: Given a successful DELETE, the mutation resolves without data.
  it("calls the DELETE endpoint for the given id", async () => {
    mockDelete.mockResolvedValueOnce(undefined);
    const { result } = renderHook(() => useDeleteDocument(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("doc-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockDelete).toHaveBeenCalledWith(
      API_ENDPOINTS.DOCUMENT_BY_ID("doc-1"),
      { method: "DELETE" },
    );
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
