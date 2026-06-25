"use client";

import { useMemo } from "react";
import { format } from "date-fns";
import {
  buildCalendarDaysFromApi,
  buildEmptyCalendarDays,
  calendarGridRange,
} from "@/modules/editorial-operations";
import type { CalendarDay } from "@/modules/editorial-operations";
import { useContentCalendar } from "@/modules/editorial";

type UseCalendarDaysResult = {
  days: CalendarDay[];
  loading: boolean;
  error: string | null;
};

// Naive wall-clock ISO (no offset); the backend treats naive datetimes as UTC.
const WINDOW_FORMAT = "yyyy-MM-dd'T'HH:mm:ss";

/**
 * Loads the content calendar for the month anchored at `anchor` and derives the
 * month-grid days. The fetch is scoped to the visible grid window (passed as
 * `start`/`end` to `/api/content-calendar`), and items are placed on their true
 * date by `buildCalendarDaysFromApi`.
 */
export function useCalendarDays(anchor: Date): UseCalendarDaysResult {
  const { start, end } = useMemo(() => {
    const range = calendarGridRange(anchor);
    return {
      start: format(range.start, WINDOW_FORMAT),
      end: format(range.end, WINDOW_FORMAT),
    };
  }, [anchor]);

  const { calendar, loading, error } = useContentCalendar(start, end);

  const days = useMemo(
    () =>
      calendar && calendar.items.length > 0
        ? buildCalendarDaysFromApi(anchor, calendar.items)
        : buildEmptyCalendarDays(anchor),
    [anchor, calendar],
  );

  return { days, loading, error };
}
