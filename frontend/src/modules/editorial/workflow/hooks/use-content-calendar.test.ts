import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";

/**
 * the latest one (see tests/features/calendar-month-navigation.feature).
 */
// Scenario: fast month navigation must not let a slow stale window overwrite

vi.mock("next-intl", () => {
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
  return { ok: true, json: () => Promise.resolve(body) } as unknown as Response;
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

    rerender({ start: "B0", end: "B1" });
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));

    await act(() => {
      second.resolve(
        jsonResponse({ items: [], start: "B0", end: "B1", total: 0 }),
      );
      return Promise.resolve();
    });
    await waitFor(() => expect(result.current.calendar?.start).toBe("B0"));

    await act(() => {
      first.resolve(
        jsonResponse({ items: [], start: "A0", end: "A1", total: 0 }),
      );
      return Promise.resolve();
    });
    expect(result.current.calendar?.start).toBe("B0");
  });

  it("scopes the request to the provided start/end window", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ items: [], start: "S", end: "E", total: 0 }),
    );

    renderHook(() => useContentCalendar("S", "E"));

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    const url = mockFetch.mock.calls[0]![0];
    expect(url).toContain("start=S");
    expect(url).toContain("end=E");
  });

  // Scenario: A failed sync does not claim to be up to date
  it("resolves refetch true on success and false on failure", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ items: [], start: "A0", end: "A1", total: 0 }),
    );
    const { result } = renderHook(() => useContentCalendar("A0", "A1"));
    await waitFor(() => expect(result.current.calendar).not.toBeNull());

    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.refetch();
    });
    expect(ok).toBe(true);

    mockFetch.mockResolvedValueOnce({ ok: false } as Response);
    await act(async () => {
      ok = await result.current.refetch();
    });
    expect(ok).toBe(false);
    expect(result.current.error).toBe("loadCalendarFailed");
  });
});
