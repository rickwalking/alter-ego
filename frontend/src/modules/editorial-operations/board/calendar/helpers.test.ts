import { describe, expect, it } from "vitest";
import { getDay } from "date-fns";
import {
  buildCalendarDaysFromApi,
  buildEmptyCalendarDays,
  buildMonthGrid,
  calendarGridRange,
} from "./helpers";
import { CALENDAR_WEEK_STARTS_ON } from "./constants";
import type { CalendarItem } from "@/modules/editorial";

// Scenarios: see tests/features/calendar-month-navigation.feature

function curDays(anchor: Date): number[] {
  return buildMonthGrid(anchor)
    .filter((cell) => cell.cur)
    .map((cell) => cell.day);
}

function makeItem(overrides: Partial<CalendarItem>): CalendarItem {
  return {
    id: "id-1",
    content_type: "carousel",
    title: "Launch",
    status: "scheduled",
    event_date: "2026-07-10",
    ...overrides,
  };
}

describe("buildMonthGrid", () => {
  it("renders all days of a 31-day month as in-month cells", () => {
    // Scenario: the grid shows the anchor month's days (January 2026)
    expect(curDays(new Date(2026, 0, 1))).toEqual(
      Array.from({ length: 31 }, (_, i) => i + 1),
    );
  });

  it("renders all 28 days of a non-leap February", () => {
    // 2026 is not a leap year -> February has 28 days
    expect(curDays(new Date(2026, 1, 1))).toEqual(
      Array.from({ length: 28 }, (_, i) => i + 1),
    );
  });

  it("renders all 29 days of a leap February", () => {
    // 2028 is a leap year -> February has 29 days
    expect(curDays(new Date(2028, 1, 1))).toEqual(
      Array.from({ length: 29 }, (_, i) => i + 1),
    );
  });

  it("produces full weeks starting on the configured week-start day", () => {
    const grid = buildMonthGrid(new Date(2026, 1, 1));
    expect(grid.length % 7).toBe(0);
    expect(getDay(new Date(`${grid[0].iso}T00:00:00`))).toBe(
      CALENDAR_WEEK_STARTS_ON,
    );
  });

  it("pads to whole weeks with the in-month days as one contiguous block", () => {
    // Scenario: weekday alignment with previous/next month padding days.
    // July 2026 starts mid-week and ends mid-week, so it has both pads.
    const grid = buildMonthGrid(new Date(2026, 6, 1));
    const firstInMonth = grid.findIndex((cell) => cell.cur);
    const lastInMonth =
      grid.length - 1 - [...grid].reverse().findIndex((c) => c.cur);
    expect(firstInMonth).toBeGreaterThan(0);
    expect(grid.slice(0, firstInMonth).every((cell) => !cell.cur)).toBe(true);
    expect(grid.slice(lastInMonth + 1).every((cell) => !cell.cur)).toBe(true);
    expect(grid.slice(firstInMonth, lastInMonth + 1).every((c) => c.cur)).toBe(
      true,
    );
  });

  it("flags at most one cell as today and none for a far-past month", () => {
    // today highlighting is clock-driven; a 2000 anchor can never contain today
    const past = buildMonthGrid(new Date(2000, 0, 1));
    expect(past.every((cell) => !cell.today)).toBe(true);
  });
});

describe("calendarGridRange", () => {
  it("spans from the first visible cell to the last visible cell", () => {
    const grid = buildMonthGrid(new Date(2026, 6, 1));
    const { start, end } = calendarGridRange(new Date(2026, 6, 1));
    expect(getDay(start)).toBe(CALENDAR_WEEK_STARTS_ON);
    expect(start.getDate()).toBe(grid[0].day);
    expect(end.getDate()).toBe(grid.at(-1)?.day);
  });
});

describe("buildCalendarDaysFromApi", () => {
  it("places an event on its true calendar date", () => {
    // Scenario: events appear on their real date (July 2026)
    const grid = buildCalendarDaysFromApi(new Date(2026, 6, 1), [
      makeItem({ event_date: "2026-07-10" }),
    ]);
    const cell = grid.find((c) => c.iso === "2026-07-10");
    expect(cell?.events).toHaveLength(1);
    expect(cell?.events[0].title).toBe("Launch");
  });

  it("does not bleed an event from another month onto the same day-of-month", () => {
    // Scenario: an August 10 item must not show on July 10
    const grid = buildCalendarDaysFromApi(new Date(2026, 6, 1), [
      makeItem({ event_date: "2026-08-10", title: "August launch" }),
    ]);
    expect(grid.find((c) => c.iso === "2026-07-10")?.events).toHaveLength(0);
  });

  it("matches by the date prefix so a UTC time component cannot shift the day", () => {
    // Timezone-stability: slice(0,10) keeps the backend's calendar date
    const grid = buildCalendarDaysFromApi(new Date(2026, 6, 1), [
      makeItem({ event_date: "2026-07-10T23:30:00Z" }),
    ]);
    expect(grid.find((c) => c.iso === "2026-07-10")?.events).toHaveLength(1);
  });

  it("falls back to an empty grid shape when there are no items", () => {
    const empty = buildEmptyCalendarDays(new Date(2026, 6, 1));
    expect(empty.every((cell) => cell.events.length === 0)).toBe(true);
    expect(empty.some((cell) => cell.cur)).toBe(true);
  });
});
