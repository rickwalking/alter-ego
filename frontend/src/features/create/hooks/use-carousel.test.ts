import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import {
  useCreateCarousel,
  useCarouselProject,
  useDeleteCarousel,
} from "./use-carousel";
import { API_ENDPOINTS } from "@/constants/api";

vi.mock("@/lib/api-client", () => ({
  apiCall: vi.fn(),
}));

import { apiCall } from "@/lib/api-client";
const mockApiCall = vi.mocked(apiCall);

const MOCK_PROJECT = {
  id: "abc-123",
  topic: "React Testing",
  audience: "Developers",
  niche: "Frontend",
  title: "Mastering React Testing",
  subtitle: "A comprehensive guide",
  theme: "developer_skills",
  status: "pending",
  blog_markdown: null,
  blog_translations: null,
  caption: null,
  design_tokens: null,
  created_at: "2026-04-20T00:00:00Z",
  updated_at: "2026-04-20T00:00:00Z",
};

const MOCK_CREATE_REQUEST = {
  topic: "React Testing",
  audience: "Developers",
  niche: "Frontend",
  theme: "auto",
  image_model: "gemini" as const,
  image_style: "comic_neon" as const,
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

describe("useCreateCarousel", () => {
  it("calls the API with correct endpoint and method", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_PROJECT);
    const { result } = renderHook(() => useCreateCarousel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(MOCK_CREATE_REQUEST);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSELS,
      expect.anything(),
      {
        method: "POST",
        body: JSON.stringify(MOCK_CREATE_REQUEST),
      },
    );
  });

  it("returns the created project on success", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_PROJECT);
    const { result } = renderHook(() => useCreateCarousel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(MOCK_CREATE_REQUEST);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_PROJECT);
  });

  it("invalidates the carousels query key on success", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_PROJECT);
    const queryClient = createQueryClient();
    queryClient.setQueryData(
      ["carousels"],
      [
        {
          ...MOCK_PROJECT,
          id: "old-project",
          topic: "Old topic",
        },
      ],
    );
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useCreateCarousel(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate(MOCK_CREATE_REQUEST);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["carousels"],
    });
    expect(queryClient.getQueryData(["carousel", "abc-123"])).toEqual(
      MOCK_PROJECT,
    );
  });

  it("returns error state on API failure", async () => {
    mockApiCall.mockRejectedValueOnce(new Error("API Error"));
    const { result } = renderHook(() => useCreateCarousel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(MOCK_CREATE_REQUEST);

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toEqual(new Error("API Error"));
  });
});

describe("useCarouselProject", () => {
  it("fetches a project by ID", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_PROJECT);
    const { result } = renderHook(() => useCarouselProject("abc-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_PROJECT);
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_BY_ID("abc-123"),
      expect.anything(),
    );
  });

  it("is disabled when ID is null", () => {
    const { result } = renderHook(() => useCarouselProject(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockApiCall).not.toHaveBeenCalled();
  });
});

describe("useDeleteCarousel", () => {
  it("removes project from cache on success", async () => {
    mockApiCall.mockResolvedValueOnce({});
    const queryClient = createQueryClient();
    const removeQueries = vi.spyOn(queryClient, "removeQueries");
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useDeleteCarousel(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate("abc-123");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_BY_ID("abc-123"),
      expect.any(Object),
      { method: "DELETE" },
    );
    expect(removeQueries).toHaveBeenCalledWith({
      queryKey: ["carousel", "abc-123"],
    });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["carousels"],
    });
  });

  it("surfaces API errors", async () => {
    mockApiCall.mockRejectedValueOnce(new Error("not found"));
    const { result } = renderHook(() => useDeleteCarousel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("abc-123");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toEqual(new Error("not found"));
  });
});
