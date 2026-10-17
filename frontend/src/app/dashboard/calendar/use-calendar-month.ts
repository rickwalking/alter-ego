"use client";

import { useCallback, useMemo, useState } from "react";
import { useLocale } from "next-intl";
import { addMonths, startOfMonth, subMonths } from "date-fns";
import { formatCalendarTitle } from "@/modules/editorial-operations";

export type UseCalendarMonthResult = {
  /** First day of the viewed month (stable state used to derive the grid). */
  anchor: Date;
  /** Viewed month in the active locale, e.g. "June 2026" / "Junho de 2026". */
  title: string;
  goPrev: () => void;
  goNext: () => void;
  goToday: () => void;
};

/**
 * Owns the viewed-month anchor, defaulting to the current month. The anchor is
 * normalized to the first of the month so the grid and the fetch window derive
 * deterministically and the value stays referentially stable between renders.
 */
export function useCalendarMonth(): UseCalendarMonthResult {
  const locale = useLocale();
  const [anchor, setAnchor] = useState<Date>(() => startOfMonth(new Date()));

  const goPrev = useCallback(() => {
    setAnchor((current) => subMonths(current, 1));
  }, []);
  const goNext = useCallback(() => {
    setAnchor((current) => addMonths(current, 1));
  }, []);
  const goToday = useCallback(() => {
    setAnchor(startOfMonth(new Date()));
  }, []);

  const title = useMemo(
    () => formatCalendarTitle(anchor, locale),
    [anchor, locale],
  );

  return { anchor, title, goPrev, goNext, goToday };
}
