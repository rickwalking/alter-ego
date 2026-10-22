/**
 * Scenarios: tests/features/calendar-month-navigation.feature and
 * tests/features/calendar-today-timezone-ae0462.feature.
 */
import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCalendarMonth } from "./use-calendar-month";

const OCT_21 = new Date(2026, 9, 21);

describe("useCalendarMonth", () => {
  // Scenario: Calendar opens on the current month
  it("opens on the month of the given local today", () => {
    const { result } = renderHook(() => useCalendarMonth(OCT_21));
    expect(result.current.anchor).toEqual(new Date(2026, 9, 1));
    expect(result.current.title).toBe("October 2026");
  });

  // Scenario: The server render highlights no day
  it("has no month while today is unknown", () => {
    const { result } = renderHook(() => useCalendarMonth(null));
    expect(result.current.anchor).toBeNull();
    expect(result.current.title).toBe("");
  });

  // Scenario: The calendar opens on the viewer's local month at a month boundary
  it("uses the local month on the last evening of a month", () => {
    const { result } = renderHook(() =>
      useCalendarMonth(new Date(2026, 9, 31, 21, 30)),
    );
    expect(result.current.title).toBe("October 2026");
  });

  // Scenario: Navigating to the next month
  // Scenario: Navigating to the previous month
  it("advances and rewinds by one month", () => {
    const { result } = renderHook(() => useCalendarMonth(OCT_21));

    act(() => result.current.goNext());
    expect(result.current.title).toBe("November 2026");

    act(() => {
      result.current.goPrev();
      result.current.goPrev();
    });
    expect(result.current.title).toBe("September 2026");
  });

  // Scenario: Returning to the current month
  // Scenario: Month navigation is relative to the local month
  it("returns to the local month from anywhere via Today", () => {
    const { result } = renderHook(() => useCalendarMonth(OCT_21));

    act(() => {
      result.current.goNext();
      result.current.goNext();
      result.current.goToday();
    });
    expect(result.current.title).toBe("October 2026");
  });

  // Scenario: Today moves on at local midnight while the page stays open
  it("follows today into the next month while viewing the current one", () => {
    const { result, rerender } = renderHook(
      ({ today }: { today: Date }) => useCalendarMonth(today),
      { initialProps: { today: new Date(2026, 9, 31) } },
    );
    rerender({ today: new Date(2026, 10, 1) });
    expect(result.current.title).toBe("November 2026");
  });
});
