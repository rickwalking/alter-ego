import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useCarouselPublicPostHref } from "./use-carousel-public-post-href";

const apiCall = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiCall }));

let client: QueryClient;

function wrapper({ children }: { children: ReactNode }): React.ReactElement {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function list(ids: string[]): object {
  return {
    items: ids.map((id) => ({ id })),
    total: ids.length,
    limit: 1,
    offset: 0,
  };
}

describe("useCarouselPublicPostHref", () => {
  beforeEach(() => {
    apiCall.mockReset();
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  });

  // Scenario: The workspace links the carousel's published blog post
  it("asks the public list for the carousel's post and links it", async () => {
    apiCall.mockResolvedValue(list(["b1"]));
    const { result } = renderHook(() => useCarouselPublicPostHref("c1"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.href).toBe("/blog/b1"));
    expect(apiCall).toHaveBeenCalledWith(
      "/api/public/blog-posts?project_id=c1&limit=1",
      expect.anything(),
    );
  });

  // Scenario: The workspace hides View Blog Post when the carousel has no published post
  it("has no href when the carousel has no published post", async () => {
    apiCall.mockResolvedValue(list([]));
    const { result } = renderHook(() => useCarouselPublicPostHref("c1"), {
      wrapper,
    });
    await waitFor(() => expect(apiCall).toHaveBeenCalled());
    expect(result.current.href).toBeNull();
  });

  // Scenario: The workspace hides View Blog Post when the carousel has no published post
  it("has no href when the lookup fails", async () => {
    apiCall.mockRejectedValue(new Error("down"));
    const { result } = renderHook(() => useCarouselPublicPostHref("c1"), {
      wrapper,
    });
    await waitFor(() => expect(apiCall).toHaveBeenCalled());
    expect(result.current.href).toBeNull();
  });
});
