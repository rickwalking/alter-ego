/**
 * Scenarios: tests/features/calendar-week-day-views.feature and
 * tests/features/calendar-month-navigation.feature.
 */
import { afterEach, describe, expect, it } from "vitest";
import { format } from "date-fns";
import type { CalendarItem } from "@/modules/editorial";
import {
  buildCalendarViewDays,
  calendarViewRange,
  formatCalendarViewTitle,
  parseCalendarFocus,
  parseCalendarView,
  shiftCalendarFocus,
  toCalendarDateParam,
} from "./view-helpers";
import { buildCalendarDaysFromApi } from "./helpers";

const ORIGINAL_TZ = process.env.TZ;

function restoreTimeZone(): void {
  if (ORIGINAL_TZ === undefined) {
    delete process.env.TZ;
  } else {
    process.env.TZ = ORIGINAL_TZ;
  }
}
const WEDNESDAY = new Date(2026, 9, 21);
const ISO = "yyyy-MM-dd";

function makeItem(overrides: Partial<CalendarItem>): CalendarItem {
  return {
    id: "item-1",
    content_type: "blog",
    title: "Launch",
    status: "scheduled",
    event_date: "2026-10-21",
    ...overrides,
  };
}

function eventsOn(days: { iso: string; events: unknown[] }[], iso: string) {
  return days.find((day) => day.iso === iso)?.events ?? [];
}

afterEach(() => {
  restoreTimeZone();
});

describe("parseCalendarView", () => {
  // Scenario: The calendar opens on the month view by default
  it("defaults to month without a view param", () => {
    expect(parseCalendarView(null)).toBe("month");
  });

  // Scenario: An unknown view in the URL falls back to the month view
  it("falls back to month for an unknown view", () => {
    expect(parseCalendarView("year")).toBe("month");
  });

  it("accepts week and day", () => {
    expect(parseCalendarView("week")).toBe("week");
    expect(parseCalendarView("day")).toBe("day");
  });
});

describe("parseCalendarFocus", () => {
  // Scenario: The view and date are restored from the URL
  it("reads a yyyy-MM-dd date as that local day", () => {
    const focus = parseCalendarFocus("2026-10-30", WEDNESDAY);
    expect(format(focus, ISO)).toBe("2026-10-30");
    expect(focus.getHours()).toBe(0);
  });

  it("uses the start of today when the date is absent", () => {
    const now = new Date(2026, 9, 21, 15, 30);
    expect(parseCalendarFocus(null, now)).toEqual(WEDNESDAY);
  });

  it("uses today for a malformed or impossible date", () => {
    expect(parseCalendarFocus("21/10/2026", WEDNESDAY)).toEqual(WEDNESDAY);
    expect(parseCalendarFocus("2026-13-45", WEDNESDAY)).toEqual(WEDNESDAY);
  });

  it("round-trips through the URL date param", () => {
    expect(toCalendarDateParam(new Date(2026, 0, 5, 23, 59))).toBe(
      "2026-01-05",
    );
  });
});

describe("calendarViewRange", () => {
  // Scenario: Switching to the week view shows the focused week
  it("spans Sunday to Saturday of the focused week", () => {
    const { start, end } = calendarViewRange("week", WEDNESDAY);
    expect(start).toEqual(new Date(2026, 9, 18));
    expect(end).toEqual(new Date(2026, 9, 24, 23, 59, 59, 999));
  });

  it("spans the focused day only in the day view", () => {
    const { start, end } = calendarViewRange("day", WEDNESDAY);
    expect(start).toEqual(WEDNESDAY);
    expect(end).toEqual(new Date(2026, 9, 21, 23, 59, 59, 999));
  });

  it("spans the padded month grid in the month view", () => {
    const { start, end } = calendarViewRange("month", WEDNESDAY);
    expect(start).toEqual(new Date(2026, 8, 27));
    expect(format(end, ISO)).toBe("2026-10-31");
  });
});

describe("shiftCalendarFocus", () => {
  // Scenario: Previous and next move by one week in the week view
  it("moves a week at a time in the week view", () => {
    expect(format(shiftCalendarFocus("week", WEDNESDAY, 1), ISO)).toBe(
      "2026-10-28",
    );
    expect(format(shiftCalendarFocus("week", WEDNESDAY, -1), ISO)).toBe(
      "2026-10-14",
    );
  });

  // Scenario: Previous and next move by one day in the day view
  it("moves a day at a time in the day view", () => {
    expect(format(shiftCalendarFocus("day", WEDNESDAY, 1), ISO)).toBe(
      "2026-10-22",
    );
    expect(format(shiftCalendarFocus("day", WEDNESDAY, -1), ISO)).toBe(
      "2026-10-20",
    );
  });

  // Scenario: Navigating to the next month
  it("moves to the first of the next or previous month in the month view", () => {
    expect(format(shiftCalendarFocus("month", WEDNESDAY, 1), ISO)).toBe(
      "2026-11-01",
    );
    expect(format(shiftCalendarFocus("month", WEDNESDAY, -1), ISO)).toBe(
      "2026-09-01",
    );
  });
});

describe("buildCalendarViewDays", () => {
  it("builds seven in-range days for the week view", () => {
    const days = buildCalendarViewDays(
      { view: "week", focus: WEDNESDAY, today: null },
      [],
    );
    expect(days.map((day) => day.iso)).toEqual([
      "2026-10-18",
      "2026-10-19",
      "2026-10-20",
      "2026-10-21",
      "2026-10-22",
      "2026-10-23",
      "2026-10-24",
    ]);
    expect(days.every((day) => day.cur)).toBe(true);
  });

  it("builds the focused day alone for the day view", () => {
    const days = buildCalendarViewDays(
      { view: "day", focus: WEDNESDAY, today: null },
      [
        makeItem({ event_date: "2026-10-21" }),
        makeItem({ id: "other", event_date: "2026-10-22" }),
      ],
    );
    expect(days).toHaveLength(1);
    expect(days[0]!.events.map((event) => event.id)).toEqual(["item-1"]);
  });

  it("builds the month grid for the month view", () => {
    const days = buildCalendarViewDays(
      { view: "month", focus: WEDNESDAY, today: null },
      [],
    );
    expect(days).toHaveLength(35);
    expect(days.filter((day) => day.cur)).toHaveLength(31);
  });

  // Scenario: Week and day items show their local time
  it("places a timestamped item on the viewer's local date and keeps its instant", () => {
    process.env.TZ = "America/Sao_Paulo";
    const days = buildCalendarViewDays(
      { view: "week", focus: new Date(2026, 9, 21), today: null },
      [makeItem({ event_date: "2026-10-22T01:00:00Z" })],
    );
    expect(eventsOn(days, "2026-10-21")).toEqual([
      expect.objectContaining({ at: "2026-10-22T01:00:00Z" }),
    ]);
    expect(eventsOn(days, "2026-10-22")).toHaveLength(0);
  });

  // Scenario: A date-only item is listed as all day
  it("keeps a date-only item on its date with no time", () => {
    process.env.TZ = "America/Los_Angeles";
    const days = buildCalendarViewDays(
      { view: "day", focus: new Date(2026, 9, 21), today: null },
      [makeItem({ event_date: "2026-10-21" })],
    );
    expect(days[0]!.events).toEqual([
      expect.objectContaining({ id: "item-1", at: undefined }),
    ]);
  });
});

describe("month placement across timezones", () => {
  // Scenario: A timestamped event is placed on the viewer's local date
  it("puts 01:00Z on July 11 on July 10 in Sao Paulo", () => {
    process.env.TZ = "America/Sao_Paulo";
    const grid = buildCalendarDaysFromApi(
      new Date(2026, 6, 1),
      [makeItem({ event_date: "2026-07-11T01:00:00Z" })],
      null,
    );
    expect(eventsOn(grid, "2026-07-10")).toHaveLength(1);
    expect(eventsOn(grid, "2026-07-11")).toHaveLength(0);
  });

  it("puts the same instant on July 11 in Tokyo", () => {
    process.env.TZ = "Asia/Tokyo";
    const grid = buildCalendarDaysFromApi(
      new Date(2026, 6, 1),
      [makeItem({ event_date: "2026-07-11T01:00:00Z" })],
      null,
    );
    expect(eventsOn(grid, "2026-07-11")).toHaveLength(1);
  });

  // Scenario: A date-only event keeps its date in every timezone
  it("keeps a date-only event on its date west and east of UTC", () => {
    for (const zone of ["America/Los_Angeles", "Asia/Tokyo"]) {
      process.env.TZ = zone;
      const grid = buildCalendarDaysFromApi(
        new Date(2026, 6, 1),
        [makeItem({ event_date: "2026-07-10" })],
        null,
      );
      expect(eventsOn(grid, "2026-07-10")).toHaveLength(1);
    }
  });

  it("keeps the date prefix of an unparseable timestamp", () => {
    const grid = buildCalendarDaysFromApi(
      new Date(2026, 6, 1),
      [makeItem({ event_date: "2026-07-10Tnot-a-time" })],
      null,
    );
    expect(eventsOn(grid, "2026-07-10")).toHaveLength(1);
  });
});

describe("formatCalendarViewTitle", () => {
  it("titles the week as a date range", () => {
    expect(formatCalendarViewTitle("week", WEDNESDAY, "en")).toMatch(
      /^Oct 18\s–\s24, 2026$/,
    );
  });

  it("titles a week across years with both years", () => {
    expect(
      formatCalendarViewTitle("week", new Date(2026, 11, 30), "en"),
    ).toMatch(/^Dec 27, 2026\s–\sJan 2, 2027$/);
  });

  it("titles the day with its weekday", () => {
    expect(formatCalendarViewTitle("day", WEDNESDAY, "en")).toBe(
      "Wednesday, October 21, 2026",
    );
  });

  it("titles the month as before", () => {
    expect(formatCalendarViewTitle("month", WEDNESDAY, "en")).toBe(
      "October 2026",
    );
  });

  // Scenario: Week and day labels follow the active locale
  it("titles the week and the day in Portuguese", () => {
    expect(formatCalendarViewTitle("week", WEDNESDAY, "pt")).toMatch(
      /^18\s–\s24 de out\. de 2026$/,
    );
    expect(formatCalendarViewTitle("day", WEDNESDAY, "pt")).toBe(
      "Quarta-feira, 21 de outubro de 2026",
    );
  });
});
