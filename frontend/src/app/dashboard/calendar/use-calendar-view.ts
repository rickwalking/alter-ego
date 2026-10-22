"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale } from "next-intl";
import {
  CALENDAR_DATE_PARAM,
  CALENDAR_DEFAULT_VIEW,
  CALENDAR_VIEW_PARAM,
  formatCalendarViewTitle,
  parseCalendarFocus,
  parseCalendarView,
  shiftCalendarFocus,
  toCalendarDateParam,
} from "@/modules/editorial-operations";
import type { CalendarView } from "@/modules/editorial-operations";
import type {
  CalendarHistoryEntry,
  CalendarUrlState,
  UseCalendarViewResult,
} from "@/app/dashboard/calendar/types";

/** `?view=…&date=…` for the state; the default view and today stay out of the URL. */
function calendarHref(pathname: string, state: CalendarUrlState): string {
  const params = new URLSearchParams();
  if (state.view !== CALENDAR_DEFAULT_VIEW) {
    params.set(CALENDAR_VIEW_PARAM, state.view);
  }
  if (state.focus) {
    params.set(CALENDAR_DATE_PARAM, toCalendarDateParam(state.focus));
  }
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

/**
 * Owns the toolbar state (view + focused date) in the URL, so a reload or a
 * shared link keeps the same month, week or day. Changing the view or opening
 * a day pushes a history entry (Back returns to the previous view); stepping
 * prev/next/today replaces it, so Back does not walk every week. Month is the
 * default view and today the default date. `today` is the viewer's local day
 * (null during the server render, see `useClientToday`); until it is known the
 * focus is null and nothing is shown. The focus is derived from the URL string
 * and `today`, so it stays referentially stable between renders.
 */
export function useCalendarView(today: Date | null): UseCalendarViewResult {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const view = parseCalendarView(searchParams.get(CALENDAR_VIEW_PARAM));
  const rawDate = searchParams.get(CALENDAR_DATE_PARAM);
  const focus = useMemo(
    () => (today ? parseCalendarFocus(rawDate, today) : null),
    [rawDate, today],
  );

  const navigate = useCallback(
    (state: CalendarUrlState, entry: CalendarHistoryEntry = "replace") => {
      router[entry](calendarHref(pathname, state), { scroll: false });
    },
    [router, pathname],
  );

  const actions = useMemo(() => {
    const step = (delta: 1 | -1): void => {
      if (focus) {
        navigate({ view, focus: shiftCalendarFocus(view, focus, delta) });
      }
    };
    return {
      goPrev: () => step(-1),
      goNext: () => step(1),
      goToday: () => navigate({ view }),
      setView: (next: CalendarView) =>
        navigate(
          { view: next, focus: rawDate && focus ? focus : undefined },
          "push",
        ),
      openDay: (day: Date) => navigate({ view: "day", focus: day }, "push"),
    };
  }, [navigate, view, focus, rawDate]);

  const title = useMemo(
    () => (focus ? formatCalendarViewTitle(view, focus, locale) : ""),
    [view, focus, locale],
  );

  return { view, focus, title, ...actions };
}
