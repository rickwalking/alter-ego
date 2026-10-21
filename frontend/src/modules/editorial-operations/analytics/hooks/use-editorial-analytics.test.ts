import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useEditorialAnalytics } from "./use-editorial-analytics";

const fetchMock = vi.fn<(url: string) => Promise<Response>>();

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (url: string) => fetchMock(url),
}));

function respond(status: number, body: unknown = {}): Response {
  return new Response(JSON.stringify(body), { status });
}

describe("useEditorialAnalytics", () => {
  beforeEach(() => fetchMock.mockReset());

  // Scenario: Analytics flag off
  it.each([404, 403])("treats %i as disabled, not an error", async (status) => {
    fetchMock.mockResolvedValue(respond(status));
    const { result } = renderHook(() => useEditorialAnalytics());
    await waitFor(() => expect(result.current.disabled).toBe(true));
    expect(result.current.error).toBeNull();
    expect(result.current.data).toBeNull();
  });

  it("reports a server failure as an error", async () => {
    fetchMock.mockResolvedValue(respond(500));
    const { result } = renderHook(() => useEditorialAnalytics());
    await waitFor(() =>
      expect(result.current.error).toBe("Failed to load analytics"),
    );
    expect(result.current.disabled).toBe(false);
  });

  it("returns the analytics on success", async () => {
    const body = { summary: { total_posts: 1 }, velocity_by_week: [] };
    fetchMock.mockResolvedValue(respond(200, body));
    const { result } = renderHook(() => useEditorialAnalytics());
    await waitFor(() => expect(result.current.data).toEqual(body));
    expect(result.current.disabled).toBe(false);
  });
});
