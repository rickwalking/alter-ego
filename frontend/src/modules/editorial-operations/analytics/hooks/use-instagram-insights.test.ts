import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { API_ENDPOINTS } from "@/constants/api";

vi.mock("@/lib/api-client", () => ({
  apiCall: vi.fn(),
}));

import { apiCall } from "@/lib/api-client";
import { instagramInsightsSchema } from "./instagram-insights-schema";
import { useInstagramInsights } from "./use-instagram-insights";

const mockApiCall = vi.mocked(apiCall);

const PAYLOAD = {
  items: [],
  follows_total: null,
  follows_per_post: null,
  shares_per_100_views: null,
  configured: true,
  connector: {
    channel: "instagram",
    configured: true,
    last_sync_at: null,
    stale: false,
    error: null,
  },
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

describe("useInstagramInsights", () => {
  beforeEach(() => {
    mockApiCall.mockReset();
  });

  it("reads the instagram insights endpoint through the schema", async () => {
    mockApiCall.mockResolvedValue(PAYLOAD);

    const { result } = renderHook(() => useInstagramInsights(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toEqual(PAYLOAD));
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.INSTAGRAM_INSIGHTS,
      instagramInsightsSchema,
    );
  });
});
