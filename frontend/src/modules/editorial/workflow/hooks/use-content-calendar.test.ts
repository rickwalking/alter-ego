import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";

// Scenario: fast month navigation must not let a slow stale window overwrite
// the latest one (see tests/features/calendar-month-navigation.feature).

vi.mock("next-intl", () => {
  // Stable translator identity so the effect only re-runs when start/end change.
  const translate = (key: string): string => key;
  return { useTranslations: () => translate };
});

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useContentCalendar } from "./use-content-calendar";

const mockFetch = vi.mocked(authenticatedFetch);

function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

function jsonResponse(body: unknown): Response {
  return { ok: true, json: async () => body } as unknown as Response;
}

describe("useContentCalendar", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("ignores a slow stale response after the window changes", async () => {
    const first = deferred<Response>();
    const second = deferred<Response>();
    mockFetch
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);

    const { result, rerender } = renderHook(
      ({ start, end }) => useContentCalendar(start, end),
      { initialProps: { start: "A0", end: "A1" } },
    );

    // The window changes (next month) before the first request resolves.
    rerender({ start: "B0", end: "B1" });
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));

    // The latest (second) window resolves first and is committed.
    await act(async () => {
      second.resolve(
        jsonResponse({ items: [], start: "B0", end: "B1", total: 0 }),
      );
    });
    await waitFor(() => expect(result.current.calendar?.start).toBe("B0"));

    // The stale (first) window resolves afterwards and must NOT overwrite it.
    await act(async () => {
      first.resolve(
        jsonResponse({ items: [], start: "A0", end: "A1", total: 0 }),
      );
    });
    expect(result.current.calendar?.start).toBe("B0");
  });

  it("scopes the request to the provided start/end window", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ items: [], start: "S", end: "E", total: 0 }),
    );

    renderHook(() => useContentCalendar("S", "E"));

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("start=S");
    expect(url).toContain("end=E");
  });
});
