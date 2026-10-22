import {
  addDays,
  addMonths,
  addWeeks,
  endOfDay,
  endOfWeek,
  format,
  isValid,
  parse,
  startOfDay,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import type { CalendarItem } from "@/modules/editorial";
import { toDateLocaleTag } from "@/lib/locale-format";
import {
  CALENDAR_DATE_ONLY_PATTERN,
  CALENDAR_DAY_TITLE_FORMAT,
  CALENDAR_DEFAULT_VIEW,
  CALENDAR_ISO_DAY_FORMAT,
  CALENDAR_VIEWS,
  CALENDAR_WEEK_STARTS_ON,
  CALENDAR_WEEK_TITLE_FORMAT,
} from "./constants";
import {
  buildCalendarDays,
  buildCalendarDaysFromApi,
  calendarGridRange,
  capitalizeCalendarLabel,
  formatCalendarTitle,
  placeCalendarItems,
} from "./helpers";
import type {
  CalendarDay,
  CalendarRange,
  CalendarView,
  CalendarViewTarget,
} from "./types";

const WEEK_OPTIONS = { weekStartsOn: CALENDAR_WEEK_STARTS_ON } as const;

/** The URL `view` param as a known view; anything else is the default (month). */
export function parseCalendarView(raw: string | null): CalendarView {
  return CALENDAR_VIEWS.find((view) => view === raw) ?? CALENDAR_DEFAULT_VIEW;
}

/** The URL `date` param (`yyyy-MM-dd`) as a local date, or `today` when absent/invalid. */
export function parseCalendarFocus(raw: string | null, today: Date): Date {
  if (raw === null || !CALENDAR_DATE_ONLY_PATTERN.test(raw)) {
    return startOfDay(today);
  }
  const parsed = parse(raw, CALENDAR_ISO_DAY_FORMAT, today);
  return isValid(parsed) ? parsed : startOfDay(today);
}

/** The local `yyyy-MM-dd` written to the URL `date` param. */
export function toCalendarDateParam(date: Date): string {
  return format(date, CALENDAR_ISO_DAY_FORMAT);
}

/** Days the view shows for `focus`: the month grid, its week, or the day itself. */
export function calendarViewRange(
  view: CalendarView,
  focus: Date,
): CalendarRange {
  if (view === "week") {
    return {
      start: startOfWeek(focus, WEEK_OPTIONS),
      end: endOfWeek(focus, WEEK_OPTIONS),
    };
  }
  if (view === "day") {
    return { start: startOfDay(focus), end: endOfDay(focus) };
  }
  return calendarGridRange(focus);
}

/** Moves `focus` one month, week or day back (`-1`) or forward (`1`). */
export function shiftCalendarFocus(
  view: CalendarView,
  focus: Date,
  step: 1 | -1,
): Date {
  if (view === "week") {
    return addWeeks(focus, step);
  }
  if (view === "day") {
    return addDays(focus, step);
  }
  return addMonths(startOfMonth(focus), step);
}

/**
 * Cells of the view with the API items placed on their local date; `today`
 * (null until known on the client) marks the highlighted cell.
 */
export function buildCalendarViewDays(
  target: CalendarViewTarget,
  items: CalendarItem[],
): CalendarDay[] {
  const { view, focus, today } = target;
  if (view === "month") {
    return buildCalendarDaysFromApi(focus, items, today);
  }
  const range = calendarViewRange(view, focus);
  return placeCalendarItems(
    buildCalendarDays(range, () => true, today),
    items,
  );
}

/** Toolbar title: "October 2026", "Oct 18 – 24, 2026" or "Wednesday, October 21, 2026". */
export function formatCalendarViewTitle(
  view: CalendarView,
  focus: Date,
  locale: string,
): string {
  const tag = toDateLocaleTag(locale);
  if (view === "week") {
    const { start, end } = calendarViewRange(view, focus);
    return new Intl.DateTimeFormat(tag, CALENDAR_WEEK_TITLE_FORMAT).formatRange(
      start,
      end,
    );
  }
  if (view === "day") {
    return capitalizeCalendarLabel(
      focus.toLocaleDateString(tag, CALENDAR_DAY_TITLE_FORMAT),
      locale,
    );
  }
  return formatCalendarTitle(focus, locale);
}
