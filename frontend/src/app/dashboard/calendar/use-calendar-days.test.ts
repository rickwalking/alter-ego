import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { addDays, subDays } from "date-fns";
import { calendarGridRange } from "@/modules/editorial-operations";

// Scenario: the fetch window must cover every visible local cell for any
// timezone (see tests/features/calendar-month-navigation.feature).

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
    const anchor = new Date(2026, 5, 1); // June 2026
    renderHook(() => useCalendarDays(anchor));

    const [start, end] = mockUseContentCalendar.mock.calls[0] as [
      string,
      string,
    ];
    const range = calendarGridRange(anchor);

    expect(start).toBe(subDays(range.start, 1).toISOString());
    expect(end).toBe(addDays(range.end, 1).toISOString());
    // The sent window strictly contains the visible grid boundaries, so an
    // edge-cell event can't fall outside it regardless of the viewer's offset.
    expect(new Date(start).getTime()).toBeLessThan(range.start.getTime());
    expect(new Date(end).getTime()).toBeGreaterThan(range.end.getTime());
  });
});
