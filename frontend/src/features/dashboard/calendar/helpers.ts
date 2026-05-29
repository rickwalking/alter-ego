import { CALENDAR_TODAY } from "./constants";
import type { CalendarDay, CalendarEvent } from "./types";

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
