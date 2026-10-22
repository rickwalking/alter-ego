import {
  addDays,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameMonth,
  isSameDay,
  parseISO,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import type { CalendarItem } from "@/modules/editorial";
import { toDateLocaleTag } from "@/lib/locale-format";
import { resolveDisplayTitle } from "@/lib/public-blog-text";
import {
  CALENDAR_API_CONTENT_TYPES,
  CALENDAR_DATE_ONLY_PATTERN,
  CALENDAR_EVENT_DAY_FORMAT,
  CALENDAR_ISO_DAY_FORMAT,
  CALENDAR_TITLE_FORMAT,
  CALENDAR_WEEKDAY_FORMAT,
  CALENDAR_WEEK_STARTS_ON,
} from "./constants";
import type {
  CalendarContentType,
  CalendarDay,
  CalendarEvent,
  CalendarRange,
} from "./types";

function isApiContentType(
  raw: string,
): raw is keyof typeof CALENDAR_API_CONTENT_TYPES {
  return Object.hasOwn(CALENDAR_API_CONTENT_TYPES, raw);
}

function mapContentType(raw: string): CalendarContentType {
  return isApiContentType(raw) ? CALENDAR_API_CONTENT_TYPES[raw] : "management";
}

/** True when `value` is a plain `yyyy-MM-dd` calendar date with no time of day. */
function isDateOnly(value: string): boolean {
  return CALENDAR_DATE_ONLY_PATTERN.test(value);
}

function mapCalendarItemToEvent(item: CalendarItem): CalendarEvent {
  return {
    id: item.id,
    title: resolveDisplayTitle([item.title]),
    at: isDateOnly(item.event_date) ? undefined : item.event_date,
    contentType: mapContentType(item.content_type),
    status:
      item.phase_status === "published" ||
      item.phase_status === "approved" ||
      item.phase_status === "in_progress" ||
      item.phase_status === "awaiting_human"
        ? item.phase_status
        : undefined,
  };
}

/** First and last day rendered by the month grid anchored at `anchor`. */
export function calendarGridRange(anchor: Date): CalendarRange {
  const start = startOfWeek(startOfMonth(anchor), {
    weekStartsOn: CALENDAR_WEEK_STARTS_ON,
  });
  const end = endOfWeek(endOfMonth(anchor), {
    weekStartsOn: CALENDAR_WEEK_STARTS_ON,
  });
  return { start, end };
}

/**
 * Day key used to match an API item to a cell. A timestamped `event_date` is an
 * instant, so it lands on the viewer's LOCAL date: 22:00 in Sao Paulo on the
 * 21st is 01:00Z on the 22nd and belongs on the 21st. A date-only value already
 * is a calendar date and is used as is (parsing it would read UTC midnight and
 * shift it a day west of UTC). An unparseable value keeps its date prefix.
 */
function eventDayKey(eventDate: string): string {
  if (isDateOnly(eventDate)) {
    return eventDate;
  }
  const instant = parseISO(eventDate);
  if (Number.isNaN(instant.getTime())) {
    return eventDate.slice(0, CALENDAR_ISO_DAY_FORMAT.length);
  }
  return format(instant, CALENDAR_ISO_DAY_FORMAT);
}

/**
 * One cell per day from `range.start` to `range.end`; `isCurrent` sets `cur`.
 * `today` is the viewer's local day; null (not yet known) highlights no cell.
 */
export function buildCalendarDays(
  range: CalendarRange,
  isCurrent: (date: Date) => boolean,
  today: Date | null,
): CalendarDay[] {
  return eachDayOfInterval(range).map((date) => ({
    day: date.getDate(),
    iso: format(date, CALENDAR_ISO_DAY_FORMAT),
    cur: isCurrent(date),
    today: today !== null && isSameDay(date, today),
    events: [],
  }));
}

/** Build the month grid for `anchor`, each cell carrying its real ISO date. */
export function buildMonthGrid(
  anchor: Date,
  today: Date | null,
): CalendarDay[] {
  return buildCalendarDays(
    calendarGridRange(anchor),
    (date) => isSameMonth(date, anchor),
    today,
  );
}

/** Empty month grid (anchor month) when the API returns no scheduled items. */
export function buildEmptyCalendarDays(
  anchor: Date,
  today: Date | null,
): CalendarDay[] {
  return buildMonthGrid(anchor, today);
}

/** Place each API item on the cell of its local calendar date (see `eventDayKey`). */
export function placeCalendarItems(
  days: CalendarDay[],
  items: CalendarItem[],
): CalendarDay[] {
  const eventsByDay: Record<string, CalendarEvent[]> = {};

  for (const item of items) {
    const key = eventDayKey(item.event_date);
    const dayEvents = eventsByDay[key] ?? [];
    dayEvents.push(mapCalendarItemToEvent(item));
    eventsByDay[key] = dayEvents;
  }

  return days.map((cell) => ({
    ...cell,
    events: eventsByDay[cell.iso] ?? [],
  }));
}

/**
 * Build the anchor-month grid with API calendar items placed on their true
 * date. Items are matched to a cell by full `yyyy-MM-dd`, so an event only
 * appears in the month that contains it (no day-of-month bleed across months).
 */
export function buildCalendarDaysFromApi(
  anchor: Date,
  items: CalendarItem[],
  today: Date | null,
): CalendarDay[] {
  return placeCalendarItems(buildMonthGrid(anchor, today), items);
}

/** Upper-cases the first letter in the locale (pt "outubro" -> "Outubro"). */
export function capitalizeCalendarLabel(label: string, locale: string): string {
  return (
    label.charAt(0).toLocaleUpperCase(toDateLocaleTag(locale)) + label.slice(1)
  );
}

/** Viewed-month title in the active locale (pt "Outubro de 2026"). */
export function formatCalendarTitle(anchor: Date, locale: string): string {
  const title = anchor.toLocaleDateString(
    toDateLocaleTag(locale),
    CALENDAR_TITLE_FORMAT,
  );
  return capitalizeCalendarLabel(title, locale);
}

/** Per-event label for a `yyyy-MM-dd` cell (pt "17 de out.", en "Oct 17"). */
export function formatCalendarDayLabel(iso: string, locale: string): string {
  return parseISO(iso).toLocaleDateString(
    toDateLocaleTag(locale),
    CALENDAR_EVENT_DAY_FORMAT,
  );
}

/** Seven weekday headers from the grid's first weekday, in the locale. */
export function calendarWeekdayHeaders(locale: string): string[] {
  const tag = toDateLocaleTag(locale);
  const first = startOfWeek(new Date(), {
    weekStartsOn: CALENDAR_WEEK_STARTS_ON,
  });
  return Array.from({ length: 7 }, (_, offset) =>
    addDays(first, offset).toLocaleDateString(tag, CALENDAR_WEEKDAY_FORMAT),
  );
}
