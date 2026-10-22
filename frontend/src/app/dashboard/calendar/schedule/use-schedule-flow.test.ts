/**
 * Scenarios: tests/features/calendar-schedule-post.feature.
 */
import { describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import type { BlogPost } from "@/modules/publishing";
import { useScheduleFlow } from "./use-schedule-flow";

describe("useScheduleFlow", () => {
  // Scenario: The calendar refreshes and confirms the schedule
  it("closes, refetches and confirms after a schedule", () => {
    const refetch = vi.fn().mockResolvedValue(true);
    const { result } = renderHook(() => useScheduleFlow(refetch));
    act(() => result.current.openDialog());
    expect(result.current.open).toBe(true);

    act(() =>
      result.current.onScheduled({
        title: "Launch",
        scheduled_publish_at: "2026-10-23T23:00:00.000Z",
      } as BlogPost),
    );
    expect(result.current.open).toBe(false);
    expect(refetch).toHaveBeenCalledTimes(1);
    expect(result.current.notice).toMatch(/^“Launch” is scheduled for .+2026/);
  });

  // Scenario: Cancel closes the dialog without scheduling
  it("closes without a notice or a refetch", () => {
    const refetch = vi.fn();
    const { result } = renderHook(() => useScheduleFlow(refetch));
    act(() => result.current.openDialog());
    act(() => result.current.close());
    expect(result.current.open).toBe(false);
    expect(result.current.notice).toBeNull();
    expect(refetch).not.toHaveBeenCalled();
  });
});
