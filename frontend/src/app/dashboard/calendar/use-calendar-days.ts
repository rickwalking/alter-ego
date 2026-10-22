"use client";

import { useMemo } from "react";
import { addDays, subDays } from "date-fns";
import {
  buildCalendarViewDays,
  calendarViewRange,
} from "@/modules/editorial-operations";
import type { CalendarDay, CalendarView } from "@/modules/editorial-operations";
import { useContentCalendar } from "@/modules/editorial";

interface UseCalendarDaysResult {
  days: CalendarDay[];
  loading: boolean;
  error: string | null;
  /** Re-fetches the current window; resolves true when the new data was stored. */
  refetch: () => Promise<boolean>;
}

/**
 * Loads the content calendar for the days the view shows (the month grid, the
 * week or the day containing `focus`) and derives its cells. The fetch is
 * scoped to that window (passed as `start`/`end` to `/api/content-calendar`),
 * and items are placed on their local date by `buildCalendarViewDays`.
 *
 * The cells are LOCAL dates but the backend window is UTC: a naive
 * toISOString() of the local boundaries shifts by the viewer's offset and could
 * drop an edge-cell event. The window is padded by one day on each side so every
 * visible local cell is covered for any timezone; placement stays exact because
 * each item is matched to a cell by its local `yyyy-MM-dd`. Nothing is fetched
 * and no day is built until the focus (known only on the client) exists.
 */
export function useCalendarDays(
  view: CalendarView,
  focus: Date | null,
  today: Date | null,
): UseCalendarDaysResult {
  const window = useMemo(() => {
    if (!focus) {
      return null;
    }
    const range = calendarViewRange(view, focus);
    return {
      start: subDays(range.start, 1).toISOString(),
      end: addDays(range.end, 1).toISOString(),
    };
  }, [view, focus]);

  const { calendar, loading, error, refetch } = useContentCalendar(
    window?.start,
    window?.end,
    window !== null,
  );

  const days = useMemo(
    () =>
      focus
        ? buildCalendarViewDays({ view, focus, today }, calendar?.items ?? [])
        : [],
    [view, focus, today, calendar],
  );

  return { days, loading, error, refetch };
}
