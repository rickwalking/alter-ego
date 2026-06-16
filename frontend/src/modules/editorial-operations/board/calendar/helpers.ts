import { parseISO } from "date-fns";
import type { CalendarItem } from "@/modules/editorial";
import { CALENDAR_TODAY } from "./constants";
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

function buildMonthGridShell(): CalendarDay[] {
  const days: CalendarDay[] = [];
  for (const day of [27, 28, 29, 30]) {
    days.push({ day, cur: false, today: false, events: [] });
  }
  for (let day = 1; day <= 31; day += 1) {
    days.push({
      day,
      cur: true,
      today: day === CALENDAR_TODAY,
      events: [],
    });
  }
  return days;
}

/** Empty month grid when the API returns no scheduled items. */
export function buildEmptyCalendarDays(): CalendarDay[] {
  return buildMonthGridShell();
}

/** Build month grid days with API calendar items on event_date. */
export function buildCalendarDaysFromApi(items: CalendarItem[]): CalendarDay[] {
  const eventsByDay: Record<number, CalendarEvent[]> = {};

  for (const item of items) {
    const day = parseISO(item.event_date).getDate();
    const event = mapCalendarItemToEvent(item);
    if (!eventsByDay[day]) {
      eventsByDay[day] = [];
    }
    eventsByDay[day].push(event);
  }

  return buildMonthGridShell().map((cell) => ({
    ...cell,
    events: cell.cur ? (eventsByDay[cell.day] ?? []) : [],
  }));
}
