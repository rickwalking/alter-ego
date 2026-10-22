/**
 * Scenarios: tests/features/calendar-sync.feature.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useCalendarSync } from "./use-calendar-sync";

describe("useCalendarSync", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  // Scenario: Sync re-fetches the visible range
  // Scenario: Sync shows that it is running
  it("refetches, is busy meanwhile and records when it finished", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 22, 14, 5));
    const pendingRefetch = Promise.withResolvers<boolean>();
    const refetch = vi.fn(() => pendingRefetch.promise);
    const { result } = renderHook(() => useCalendarSync(refetch));
    expect(result.current.syncedAt).toBeNull();

    let pending: Promise<void> = Promise.resolve();
    act(() => {
      pending = result.current.sync();
    });
    expect(refetch).toHaveBeenCalledTimes(1);
    expect(result.current.syncing).toBe(true);

    await act(async () => {
      pendingRefetch.resolve(true);
      await pending;
    });
    expect(result.current.syncing).toBe(false);
    expect(result.current.syncedAt).toEqual(new Date(2026, 9, 22, 14, 5));
  });

  // Scenario: A failed sync does not claim to be up to date
  it("records no sync time when the refetch failed", async () => {
    const refetch = vi.fn().mockResolvedValue(false);
    const { result } = renderHook(() => useCalendarSync(refetch));
    await act(() => result.current.sync());
    expect(result.current.syncing).toBe(false);
    expect(result.current.syncedAt).toBeNull();
  });

  it("keeps the previous sync time after a later failure", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 22, 14, 5));
    const refetch = vi
      .fn<() => Promise<boolean>>()
      .mockResolvedValueOnce(true)
      .mockResolvedValueOnce(false);
    const { result } = renderHook(() => useCalendarSync(refetch));
    await act(() => result.current.sync());
    vi.setSystemTime(new Date(2026, 9, 22, 14, 30));
    await act(() => result.current.sync());
    expect(result.current.syncedAt).toEqual(new Date(2026, 9, 22, 14, 5));
  });

  it("stops syncing even if the refetch throws", async () => {
    const refetch = vi.fn().mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useCalendarSync(refetch));
    await act(async () => {
      await result.current.sync().catch(() => undefined);
    });
    expect(result.current.syncing).toBe(false);
    expect(result.current.syncedAt).toBeNull();
  });
});
