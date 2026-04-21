import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import {
  useCreateCarousel,
  useCarouselStatus,
  useCarouselProject,
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

const MOCK_STATUS = {
  id: "abc-123",
  status: "researching",
  error_message: null,
  updated_at: "2026-04-20T00:00:00Z",
};

const MOCK_CREATE_REQUEST = {
  topic: "React Testing",
  audience: "Developers",
  niche: "Frontend",
  theme: "auto",
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useCreateCarousel", () => {
  // Scenario: useCreateCarousel creates a carousel via POST request
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
      }
    );
  });

  // Scenario: useCreateCarousel returns the created project
  it("returns the created project on success", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_PROJECT);
    const { result } = renderHook(() => useCreateCarousel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(MOCK_CREATE_REQUEST);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_PROJECT);
  });

  // Scenario: useCreateCarousel invalidates carousels query on success
  it("invalidates the carousels query key on success", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_PROJECT);
    const { result } = renderHook(() => useCreateCarousel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(MOCK_CREATE_REQUEST);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockApiCall).toHaveBeenCalledTimes(1);
  });

  // Scenario: useCreateCarousel handles API errors
  it("returns error state on API failure", async () => {
    mockApiCall.mockRejectedValueOnce(new Error("API Error"));
    const { result } = renderHook(() => useCreateCarousel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(MOCK_CREATE_REQUEST);

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toEqual(new Error("API Error"));
  });

  // Scenario: useCreateCarousel exposes pending state
  it("shows pending state while mutation is in progress", async () => {
    let resolvePromise: (value: typeof MOCK_PROJECT) => void;
    mockApiCall.mockImplementation(
      () => new Promise((resolve) => {
        resolvePromise = resolve;
      })
    );
    const { result } = renderHook(() => useCreateCarousel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(MOCK_CREATE_REQUEST);

    await waitFor(() => expect(result.current.isPending).toBe(true));

    resolvePromise!(MOCK_PROJECT);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe("useCarouselStatus", () => {
  // Scenario: useCarouselStatus polls the status endpoint
  it("fetches status by ID", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_STATUS);
    const { result } = renderHook(() => useCarouselStatus("abc-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_STATUS);
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_STATUS("abc-123"),
      expect.anything()
    );
  });

  // Scenario: useCarouselStatus uses correct query key
  it("uses the correct query key with status and ID", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_STATUS);
    const { result } = renderHook(() => useCarouselStatus("abc-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_STATUS);
  });

  // Scenario: useCarouselStatus is disabled when ID is empty
  it("is disabled when ID is empty string", () => {
    const { result } = renderHook(() => useCarouselStatus(""), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockApiCall).not.toHaveBeenCalled();
  });

  // Scenario: useCarouselStatus is disabled when ID is null
  it("is disabled when ID is null", () => {
    const { result } = renderHook(() => useCarouselStatus(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockApiCall).not.toHaveBeenCalled();
  });

  // Scenario: useCarouselStatus configures polling interval
  it("has the correct polling interval configured", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_STATUS);
    const { result } = renderHook(() => useCarouselStatus("abc-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_STATUS);
  });
});

describe("useCarouselProject", () => {
  // Scenario: useCarouselProject fetches a single project by ID
  it("fetches a project by ID", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_PROJECT);
    const { result } = renderHook(() => useCarouselProject("abc-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_PROJECT);
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSELS + "/abc-123",
      expect.anything()
    );
  });

  // Scenario: useCarouselProject uses the correct query key
  it("uses the correct query key with carousel and ID", async () => {
    mockApiCall.mockResolvedValueOnce(MOCK_PROJECT);
    const { result } = renderHook(() => useCarouselProject("abc-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_PROJECT);
  });

  // Scenario: useCarouselProject is disabled when ID is empty
  it("is disabled when ID is empty string", () => {
    const { result } = renderHook(() => useCarouselProject(""), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockApiCall).not.toHaveBeenCalled();
  });

  // Scenario: useCarouselProject is disabled when ID is null
  it("is disabled when ID is null", () => {
    const { result } = renderHook(() => useCarouselProject(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockApiCall).not.toHaveBeenCalled();
  });

  // Scenario: useCarouselProject does not poll by default
  it("does not have a refetch interval", () => {
    mockApiCall.mockResolvedValueOnce(MOCK_PROJECT);
    const { result } = renderHook(() => useCarouselProject("abc-123"), {
      wrapper: createWrapper(),
    });

    expect(result.current.refetchInterval).toBeUndefined();
  });
});
