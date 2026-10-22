import { addMilliseconds, format, isValid, parse } from "date-fns";
import type { CalendarItem } from "@/modules/editorial";
import {
  DATETIME_LOCAL_FORMAT,
  MIN_SCHEDULE_LEAD_MS,
  SCHEDULE_CONFLICT_WINDOW_MS,
} from "./constants";
import type { ScheduleDraft, ScheduleValidationError } from "./types";

/** The viewer's IANA timezone (e.g. "America/Sao_Paulo"), shown next to the time. */
export function viewerTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

/** A `datetime-local` value as a local Date, or null when empty or malformed. */
export function parseScheduleTime(value: string): Date | null {
  if (!value) {
    return null;
  }
  const parsed = parse(value, DATETIME_LOCAL_FORMAT, new Date(0));
  return isValid(parsed) ? parsed : null;
}

/** The earliest time the backend accepts, as a `datetime-local` min value. */
export function minScheduleTime(now: Date): string {
  return format(
    addMilliseconds(now, MIN_SCHEDULE_LEAD_MS),
    DATETIME_LOCAL_FORMAT,
  );
}

/** The first rule the draft breaks: a post, a time, a time far enough ahead. */
export function validateSchedule(
  draft: ScheduleDraft,
  now: Date,
): ScheduleValidationError | null {
  if (!draft.postId) {
    return "postRequired";
  }
  const at = parseScheduleTime(draft.time);
  if (!at) {
    return "timeRequired";
  }
  return at.getTime() < now.getTime() + MIN_SCHEDULE_LEAD_MS
    ? "timeInPast"
    : null;
}

/** The content-calendar window (ISO) to check for conflicts around `at`. */
export function conflictWindow(at: Date): { start: string; end: string } {
  return {
    start: new Date(at.getTime() - SCHEDULE_CONFLICT_WINDOW_MS).toISOString(),
    end: new Date(at.getTime() + SCHEDULE_CONFLICT_WINDOW_MS).toISOString(),
  };
}

/**
 * Calendar items (blog posts and carousels) within an hour of `at`, inclusive,
 * other than the post being scheduled.
 */
export function findScheduleConflicts(
  items: CalendarItem[],
  target: { postId: string; at: Date },
): CalendarItem[] {
  return items.filter((item) => {
    if (item.id === target.postId) {
      return false;
    }
    const distance = Math.abs(
      new Date(item.event_date).getTime() - target.at.getTime(),
    );
    return distance <= SCHEDULE_CONFLICT_WINDOW_MS;
  });
}
