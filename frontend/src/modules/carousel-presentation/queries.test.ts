import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  carouselKeys,
  carouselListOptions,
  carouselProjectOptions,
} from "./queries";
import { API_ENDPOINTS } from "@/constants/api";

vi.mock("@/lib/api-client", () => ({
  apiCall: vi.fn(),
}));

import { apiCall } from "@/lib/api-client";

const mockApiCall = vi.mocked(apiCall);

beforeEach(() => {
  vi.clearAllMocks();
});

function callQueryFn(options: { queryFn?: unknown }) {
  expect(options.queryFn).toBeTypeOf("function");
  return (options.queryFn as () => Promise<unknown>)();
}

describe("carouselKeys", () => {
  it("returns stable keys for detail and slides", () => {
    expect(carouselKeys.detail("project-1")).toEqual(["carousel", "project-1"]);
    expect(carouselKeys.slides("project-1")).toEqual([
      "carousel",
      "project-1",
      "slides",
    ]);
    expect(carouselKeys.list()).toEqual(["carousels"]);
  });
});

describe("carouselListOptions", () => {
  it("does not append a query string without filters", async () => {
    mockApiCall.mockResolvedValueOnce({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    });

    await callQueryFn(carouselListOptions());

    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSELS,
      expect.anything(),
    );
  });

  it("serializes status and limit filters explicitly", async () => {
    mockApiCall.mockResolvedValueOnce({
      items: [],
      total: 0,
      limit: 2,
      offset: 0,
    });

    await callQueryFn(carouselListOptions({ status: "completed", limit: 2 }));

    expect(mockApiCall).toHaveBeenCalledWith(
      `${API_ENDPOINTS.CAROUSELS}?status=completed&limit=2`,
      expect.anything(),
    );
  });
});

describe("carouselProjectOptions", () => {
  it("uses the detail endpoint without casting disabled IDs", async () => {
    mockApiCall.mockResolvedValueOnce({ id: "project-1" });

    await callQueryFn(carouselProjectOptions("project-1"));

    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.CAROUSEL_BY_ID("project-1"),
      expect.anything(),
    );
    expect(carouselProjectOptions(null).queryFn).not.toBeTypeOf("function");
  });
});
