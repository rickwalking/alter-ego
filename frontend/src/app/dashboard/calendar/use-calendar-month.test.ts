import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { addMonths, format, startOfMonth } from "date-fns";
import { useCalendarMonth } from "./use-calendar-month";

// Scenarios: see tests/features/calendar-month-navigation.feature

const TITLE = "MMMM yyyy";

describe("useCalendarMonth", () => {
  it("defaults to the current month", () => {
    const { result } = renderHook(() => useCalendarMonth());
    expect(result.current.title).toBe(format(startOfMonth(new Date()), TITLE));
  });

  it("advances and rewinds by one month", () => {
    const { result } = renderHook(() => useCalendarMonth());
    const current = result.current.title;

    act(() => result.current.goNext());
    expect(result.current.title).toBe(
      format(addMonths(startOfMonth(new Date()), 1), TITLE),
    );

    act(() => result.current.goPrev());
    expect(result.current.title).toBe(current);
  });

  it("returns to the current month from anywhere via Today", () => {
    const { result } = renderHook(() => useCalendarMonth());
    const current = result.current.title;

    act(() => {
      result.current.goNext();
      result.current.goNext();
      result.current.goToday();
    });
    expect(result.current.title).toBe(current);
  });
});
