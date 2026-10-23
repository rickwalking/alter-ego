/**
 * Deleting a library photo: the DELETE call, the library refresh and the
 * carousels a 409 names.
 */
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-client";
import {
  creatorPhotoKeys,
  photoInUseCarousels,
  useDeleteCreatorPhoto,
} from "./use-creator-photos";

function wrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  };
}

function conflict(detail: unknown): ApiError {
  const error = new ApiError(409, "conflict");
  error.detail = detail;
  return error;
}

describe("photoInUseCarousels", () => {
  /** Scenario: A photo in use lists the carousels that use it */
  it("reads the carousels of an in-use conflict", () => {
    const error = conflict({
      code: "creator_asset_in_use",
      carousels: [{ id: "c-1", title: null }],
    });
    expect(photoInUseCarousels(error)).toEqual([{ id: "c-1", title: null }]);
  });

  /** Scenario: A photo in use lists the carousels that use it */
  it("is null for any other failure", () => {
    expect(photoInUseCarousels(null)).toBeNull();
    expect(photoInUseCarousels(new Error("x"))).toBeNull();
    expect(photoInUseCarousels(new ApiError(403, "no"))).toBeNull();
    expect(photoInUseCarousels(conflict("creator_asset_in_use"))).toBeNull();
  });
});

describe("useDeleteCreatorPhoto", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  /** Scenario: Deleting an unused photo after confirming */
  it("sends DELETE and refreshes every library list", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 204 }));
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useDeleteCreatorPhoto(), {
      wrapper: wrapper(client),
    });

    act(() => result.current.mutate("p-1"));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const [url, init] = fetchSpy.mock.calls[0]!;
    expect(url).toEqual(
      expect.stringContaining("/api/carousels/creator-assets/p-1"),
    );
    expect(init?.method).toBe("DELETE");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: creatorPhotoKeys.all });
  });
});
