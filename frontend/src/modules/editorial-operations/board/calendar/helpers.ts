import {
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameMonth,
  isToday,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import type { CalendarItem } from "@/modules/editorial";
import { CALENDAR_ISO_DAY_FORMAT, CALENDAR_WEEK_STARTS_ON } from "./constants";
import type { CalendarContentType, CalendarDay, CalendarEvent } from "./types";

function mapContentType(raw: string): CalendarContentType {
  if (raw === "carousel" || raw === "blog") {
    return raw;
  }
  if (raw === "meeting") return "meeting";
  return "management";
}

function mapCalendarItemToEvent(item: CalendarItem): CalendarEvent {
  return {
    title: item.title,
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
export function calendarGridRange(anchor: Date): { start: Date; end: Date } {
  const start = startOfWeek(startOfMonth(anchor), {
    weekStartsOn: CALENDAR_WEEK_STARTS_ON,
  });
  const end = endOfWeek(endOfMonth(anchor), {
    weekStartsOn: CALENDAR_WEEK_STARTS_ON,
  });
  return { start, end };
}

/**
 * Day key used to match an API item to a grid cell. The backend `event_date`
 * carries the authoritative calendar date; we compare its `yyyy-MM-dd` prefix
 * to each cell's local date so matching is timezone-stable (no `getDate()`
 * off-by-one across UTC offsets).
 */
function eventDayKey(eventDate: string): string {
  return eventDate.slice(0, CALENDAR_ISO_DAY_FORMAT.length);
}

/** Build the month grid for `anchor`, each cell carrying its real ISO date. */
export function buildMonthGrid(anchor: Date): CalendarDay[] {
  const { start, end } = calendarGridRange(anchor);
  return eachDayOfInterval({ start, end }).map((date) => ({
    day: date.getDate(),
    iso: format(date, CALENDAR_ISO_DAY_FORMAT),
    cur: isSameMonth(date, anchor),
    today: isToday(date),
    events: [],
  }));
}

/** Empty month grid (anchor month) when the API returns no scheduled items. */
export function buildEmptyCalendarDays(anchor: Date): CalendarDay[] {
  return buildMonthGrid(anchor);
}

/**
 * Build the anchor-month grid with API calendar items placed on their true
 * date. Items are matched to a cell by full `yyyy-MM-dd`, so an event only
 * appears in the month that contains it (no day-of-month bleed across months).
 */
export function buildCalendarDaysFromApi(
  anchor: Date,
  items: CalendarItem[],
): CalendarDay[] {
  const eventsByDay: Record<string, CalendarEvent[]> = {};

  for (const item of items) {
    const key = eventDayKey(item.event_date);
    (eventsByDay[key] ??= []).push(mapCalendarItemToEvent(item));
  }

  return buildMonthGrid(anchor).map((cell) => ({
    ...cell,
    events: eventsByDay[cell.iso] ?? [],
  }));
}
