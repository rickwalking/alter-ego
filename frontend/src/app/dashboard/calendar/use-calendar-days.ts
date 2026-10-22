"use client";

import { useMemo } from "react";
import { addDays, subDays } from "date-fns";
import {
  buildCalendarDaysFromApi,
  buildEmptyCalendarDays,
  calendarGridRange,
} from "@/modules/editorial-operations";
import type { CalendarDay } from "@/modules/editorial-operations";
import { useContentCalendar } from "@/modules/editorial";

interface UseCalendarDaysResult {
  days: CalendarDay[];
  loading: boolean;
  error: string | null;
}

/**
 * Loads the content calendar for the month anchored at `anchor` and derives the
 * month-grid days. The fetch is scoped to the visible grid window (passed as
 * `start`/`end` to `/api/content-calendar`), and items are placed on their true
 * date by `buildCalendarDaysFromApi`.
 *
 * The grid cells are LOCAL dates but the backend window is UTC: a naive
 * toISOString() of the local boundaries shifts by the viewer's offset and could
 * drop an edge-cell event. The window is padded by one day on each side so every
 * visible local cell is covered for any timezone; placement stays exact because
 * buildCalendarDaysFromApi matches each item to a cell by its yyyy-MM-dd prefix.
 * Nothing is fetched and no day is built until the anchor (the viewer's local
 * month) is known.
 */
export function useCalendarDays(
  anchor: Date | null,
  today: Date | null,
): UseCalendarDaysResult {
  const window = useMemo(() => {
    if (!anchor) {
      return null;
    }
    const range = calendarGridRange(anchor);
    return {
      start: subDays(range.start, 1).toISOString(),
      end: addDays(range.end, 1).toISOString(),
    };
  }, [anchor]);

  const { calendar, loading, error } = useContentCalendar(
    window?.start,
    window?.end,
    window !== null,
  );

  const days = useMemo(() => {
    if (!anchor) {
      return [];
    }
    return calendar && calendar.items.length > 0
      ? buildCalendarDaysFromApi(anchor, calendar.items, today)
      : buildEmptyCalendarDays(anchor, today);
  }, [anchor, calendar, today]);

  return { days, loading, error };
}
