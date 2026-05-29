import { parseISO } from "date-fns";
import type { CalendarItem } from "@/features/workflow/hooks/use-content-calendar";
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

  const days: CalendarDay[] = [];
  for (const day of [27, 28, 29, 30]) {
    days.push({ day, cur: false, today: false, events: [] });
  }
  for (let day = 1; day <= 31; day += 1) {
    days.push({
      day,
      cur: true,
      today: day === CALENDAR_TODAY,
      events: eventsByDay[day] ?? [],
    });
  }
  return days;
}

/** @deprecated Static demo events — use buildCalendarDaysFromApi in production. */
export const CALENDAR_EVENTS_BY_DAY: Record<number, CalendarEvent[]> = {
  22: [{ title: "RAG Pipeline", contentType: "blog", status: "published" }],
  24: [
    { title: "Sonnet 4 vs GPT-5", contentType: "carousel", status: "approved" },
  ],
  26: [
    {
      title: "GitHub Leak Post",
      contentType: "blog",
      status: "awaiting_human",
    },
    { title: "K8s Review", contentType: "carousel", status: "in_progress" },
  ],
  27: [{ title: "Security Sync", contentType: "meeting" }],
  28: [{ title: "Persona Review", contentType: "management" }],
  29: [
    { title: "K8s Guide Pub.", contentType: "carousel", status: "published" },
  ],
  30: [
    { title: "AI Safety Research", contentType: "blog", status: "published" },
  ],
};

export function buildCalendarDays(): CalendarDay[] {
  const days: CalendarDay[] = [];
  for (const day of [27, 28, 29, 30]) {
    days.push({ day, cur: false, today: false, events: [] });
  }
  for (let day = 1; day <= 31; day += 1) {
    days.push({
      day,
      cur: true,
      today: day === CALENDAR_TODAY,
      events: CALENDAR_EVENTS_BY_DAY[day] ?? [],
    });
  }
  return days;
}
