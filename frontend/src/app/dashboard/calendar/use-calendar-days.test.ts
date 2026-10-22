import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { addDays, subDays } from "date-fns";
import { calendarGridRange } from "@/modules/editorial-operations";

/**
 * timezone (see tests/features/calendar-month-navigation.feature).
 */
// Scenario: the fetch window must cover every visible local cell for any

const { mockUseContentCalendar } = vi.hoisted(() => ({
  mockUseContentCalendar: vi.fn(),
}));

vi.mock("@/modules/editorial", () => ({
  useContentCalendar: mockUseContentCalendar,
}));

import { useCalendarDays } from "./use-calendar-days";

describe("useCalendarDays", () => {
  beforeEach(() => {
    mockUseContentCalendar.mockReturnValue({
      calendar: null,
      loading: false,
      error: null,
    });
  });

  it("requests a window padded ±1 day around the visible grid", () => {
    const anchor = new Date(2026, 5, 1);
    renderHook(() => useCalendarDays(anchor, new Date(2026, 5, 10)));

    const [start, end] = mockUseContentCalendar.mock.calls[0] as [
      string,
      string,
    ];
    const range = calendarGridRange(anchor);

    expect(start).toBe(subDays(range.start, 1).toISOString());
    expect(end).toBe(addDays(range.end, 1).toISOString());
    expect(new Date(start).getTime()).toBeLessThan(range.start.getTime());
    expect(new Date(end).getTime()).toBeGreaterThan(range.end.getTime());
  });

  // Scenario: The server render highlights no day
  it("fetches nothing and builds no day until the local month is known", () => {
    const { result } = renderHook(() => useCalendarDays(null, null));
    expect(mockUseContentCalendar).toHaveBeenCalledWith(
      undefined,
      undefined,
      false,
    );
    expect(result.current.days).toEqual([]);
  });

  // Scenario: Today is the viewer's local date after the page loads
  it("highlights the given local today in the built month", () => {
    const { result } = renderHook(() =>
      useCalendarDays(new Date(2026, 9, 1), new Date(2026, 9, 21)),
    );
    expect(
      result.current.days.filter((day) => day.today).map((day) => day.iso),
    ).toEqual(["2026-10-21"]);
  });
});
