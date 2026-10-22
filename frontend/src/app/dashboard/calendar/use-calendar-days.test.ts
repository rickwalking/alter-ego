/**
 * Scenarios: tests/features/calendar-month-navigation.feature and
 * tests/features/calendar-week-day-views.feature.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { addDays, subDays } from "date-fns";
import { calendarGridRange } from "@/modules/editorial-operations";
import type { CalendarView } from "@/modules/editorial-operations";

const { mockUseContentCalendar } = vi.hoisted(() => ({
  mockUseContentCalendar: vi.fn(),
}));

vi.mock("@/modules/editorial", () => ({
  useContentCalendar: mockUseContentCalendar,
}));

import { useCalendarDays } from "./use-calendar-days";

function requestedWindow(view: CalendarView, focus: Date): [string, string] {
  mockUseContentCalendar.mockClear();
  renderHook(() => useCalendarDays(view, focus, null));
  return mockUseContentCalendar.mock.calls[0] as [string, string];
}

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
    const [start, end] = requestedWindow("month", anchor);
    const range = calendarGridRange(anchor);

    expect(start).toBe(subDays(range.start, 1).toISOString());
    expect(end).toBe(addDays(range.end, 1).toISOString());
    expect(new Date(start).getTime()).toBeLessThan(range.start.getTime());
    expect(new Date(end).getTime()).toBeGreaterThan(range.end.getTime());
  });

  // Scenario: The week view fetches only its own days
  it("requests only the week, padded by one day on each side", () => {
    const [start, end] = requestedWindow("week", new Date(2026, 9, 21));
    expect(start).toBe(new Date(2026, 9, 17).toISOString());
    expect(end).toBe(new Date(2026, 9, 25, 23, 59, 59, 999).toISOString());
  });

  it("requests only the day in the day view", () => {
    const [start, end] = requestedWindow("day", new Date(2026, 9, 21));
    expect(start).toBe(new Date(2026, 9, 20).toISOString());
    expect(end).toBe(new Date(2026, 9, 22, 23, 59, 59, 999).toISOString());
  });

  it("places the loaded items on the view's days", () => {
    mockUseContentCalendar.mockReturnValue({
      calendar: {
        items: [
          {
            id: "a",
            content_type: "blog",
            title: "Post",
            status: "scheduled",
            event_date: "2026-10-21",
          },
        ],
        start: "",
        end: "",
        total: 1,
      },
      loading: false,
      error: null,
    });
    const { result } = renderHook(() =>
      useCalendarDays("day", new Date(2026, 9, 21), null),
    );
    expect(result.current.days[0]!.events).toHaveLength(1);
  });

  // Scenario: The server render highlights no day
  it("fetches nothing and builds no day until the focus is known", () => {
    const { result } = renderHook(() => useCalendarDays("month", null, null));
    expect(mockUseContentCalendar).toHaveBeenCalledWith(
      undefined,
      undefined,
      false,
    );
    expect(result.current.days).toEqual([]);
  });

  // Scenario: Today is the viewer's local date after the page loads
  it("highlights the given local today in the week", () => {
    const { result } = renderHook(() =>
      useCalendarDays("week", new Date(2026, 9, 21), new Date(2026, 9, 21)),
    );
    expect(
      result.current.days.filter((day) => day.today).map((day) => day.iso),
    ).toEqual(["2026-10-21"]);
  });
});
