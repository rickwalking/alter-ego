import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { useAvailableStrategies, useRegenerateSlides } from "./use-slide-layout-strategies";
import { API_ENDPOINTS } from "@/constants/api";

vi.mock("@/lib/api-client", () => ({
  apiCall: vi.fn(),
}));

import { apiCall } from "@/lib/api-client";
const mockApiCall = vi.mocked(apiCall);

const MOCK_STRATEGIES_RESPONSE = {
  strategies: [
    { name: "intro_hero", display_name: "Intro Hero" },
    { name: "stat_card_grid", display_name: "Stat Card Grid" },
    { name: "feature_grid", display_name: "Feature Card Grid" },
  ],
};

const MOCK_APPLY_RESPONSE = {
  project_id: "proj-123",
  strategy: "feature_grid",
  message: "Slides re-rendered with new strategy",
};

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
    },
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

describe("useAvailableStrategies", () => {
  it("fetches strategy list from CAROUSEL_STRATEGIES endpoint", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_STRATEGIES_RESPONSE);
    const { result } = renderHook(() => useAvailableStrategies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_STRATEGIES,
      expect.anything(),
      { method: "GET" },
    );
    expect(result.current.data).toEqual(MOCK_STRATEGIES_RESPONSE);
  });

  it("returns error state on API failure", async () => {
    mockApiCall.mockRejectedValueOnce(new Error("Network error"));
    const { result } = renderHook(() => useAvailableStrategies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toEqual(new Error("Network error"));
  });

  it("caches the result with staleTime preventing immediate refetch", async () => {
    mockApiCall.mockResolvedValue(MOCK_STRATEGIES_RESPONSE);
    const queryClient = createQueryClient();
    const { result } = renderHook(() => useAvailableStrategies(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledTimes(1);

    mockApiCall.mockClear();
    const { result: result2 } = renderHook(() => useAvailableStrategies(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result2.current.isSuccess).toBe(true));
    expect(mockApiCall).not.toHaveBeenCalled();
    expect(result2.current.data).toEqual(MOCK_STRATEGIES_RESPONSE);
  });
});

describe("useRegenerateSlides", () => {
  it("calls PUT strategy endpoint with projectId and strategy name", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_APPLY_RESPONSE);
    const { result } = renderHook(() => useRegenerateSlides(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ projectId: "proj-123", strategy: "feature_grid" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApiCall).toHaveBeenCalledWith(
      expect.stringContaining("/api/carousels/proj-123/strategy?name=feature_grid"),
      expect.anything(),
      { method: "PUT" },
    );
    expect(result.current.data).toEqual(MOCK_APPLY_RESPONSE);
  });

  it("invalidates the project detail query on success", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_APPLY_RESPONSE);
    const queryClient = createQueryClient();
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useRegenerateSlides(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({ projectId: "proj-123", strategy: "feature_grid" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["carousel", "proj-123"],
    });
  });

  it("surfaces API errors", async () => {
    mockApiCall.mockRejectedValueOnce(new Error("Strategy not found"));
    const { result } = renderHook(() => useRegenerateSlides(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ projectId: "proj-123", strategy: "nonexistent" });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toEqual(new Error("Strategy not found"));
  });

  it("disables the button while mutation is in-flight", async () => {
    mockApiCall.mockImplementationOnce(
      () => new Promise(() => {}),
    );
    const { result } = renderHook(() => useRegenerateSlides(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ projectId: "proj-123", strategy: "feature_grid" });

    await waitFor(() => expect(result.current.isPending).toBe(true));
  });
});
