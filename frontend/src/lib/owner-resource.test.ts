import { beforeEach, describe, expect, it, vi } from "vitest";

const cookieStore = vi.hoisted(() => ({ value: "access_token=jwt" }));
vi.mock("next/headers", () => ({
  cookies: () => Promise.resolve({ toString: () => cookieStore.value }),
}));
const notFound = vi.hoisted(() =>
  vi.fn(() => {
    throw new Error("NEXT_NOT_FOUND");
  }),
);
vi.mock("next/navigation", () => ({ notFound }));

import {
  checkOwnerResource,
  notFoundUnlessOwnerResource,
} from "./owner-resource";

const ID = "0f8fad5b-d9cb-469f-a165-70867728950e";
const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  notFound.mockClear();
  vi.stubGlobal("fetch", fetchMock);
});

describe("checkOwnerResource", () => {
  // Scenario: An existing resource renders the page
  it("is found on a 2xx and forwards the session cookie", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200 });
    expect(await checkOwnerResource(`/api/carousels/${ID}`)).toBe("found");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(new RegExp(`/api/carousels/${ID}$`));
    expect(init.headers).toEqual({ cookie: "access_token=jwt" });
  });

  // Scenario: An unknown carousel workspace answers 404
  it("is missing on a 404", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 404 });
    expect(await checkOwnerResource(`/api/carousels/${ID}`)).toBe("missing");
  });

  // Scenario: A backend error leaves the page to show its own error
  it.each([[500], [401], [403]])("is unknown on a %i", async (status) => {
    fetchMock.mockResolvedValue({ ok: false, status });
    expect(await checkOwnerResource(`/api/carousels/${ID}`)).toBe("unknown");
  });

  // Scenario: A backend error leaves the page to show its own error
  it("gives up after a short timeout so a hanging backend cannot block the page", async () => {
    const timeout = vi.spyOn(AbortSignal, "timeout");
    fetchMock.mockResolvedValue({ ok: true, status: 200 });
    await checkOwnerResource(`/api/carousels/${ID}`);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(timeout).toHaveBeenCalledWith(3000);
    expect(init.signal).toBe(timeout.mock.results[0]?.value);
    timeout.mockRestore();
  });

  // Scenario: A backend error leaves the page to show its own error
  it("is unknown when the check times out", async () => {
    fetchMock.mockRejectedValue(new DOMException("timed out", "TimeoutError"));
    expect(await checkOwnerResource(`/api/carousels/${ID}`)).toBe("unknown");
  });

  // Scenario: A backend error leaves the page to show its own error
  it("is unknown when the backend is unreachable", async () => {
    fetchMock.mockRejectedValue(new Error("ECONNREFUSED"));
    expect(await checkOwnerResource(`/api/carousels/${ID}`)).toBe("unknown");
  });
});

describe("notFoundUnlessOwnerResource", () => {
  const path = (id: string): string => `/api/carousels/${id}`;

  // Scenario: A malformed id answers 404 without asking the backend
  it("is not found for a malformed id without a backend call", async () => {
    await expect(
      notFoundUnlessOwnerResource("not-a-uuid", path),
    ).rejects.toThrow("NEXT_NOT_FOUND");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  // Scenario: An unknown blog post editor answers 404
  it("is not found when the backend has no such resource", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 404 });
    await expect(notFoundUnlessOwnerResource(ID, path)).rejects.toThrow(
      "NEXT_NOT_FOUND",
    );
  });

  // Scenario: An existing resource renders the page
  it("passes for an existing resource", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200 });
    await expect(
      notFoundUnlessOwnerResource(ID, path),
    ).resolves.toBeUndefined();
    expect(notFound).not.toHaveBeenCalled();
  });

  // Scenario: A backend error leaves the page to show its own error
  it("passes when the backend answer is inconclusive", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500 });
    await expect(
      notFoundUnlessOwnerResource(ID, path),
    ).resolves.toBeUndefined();
  });
});
