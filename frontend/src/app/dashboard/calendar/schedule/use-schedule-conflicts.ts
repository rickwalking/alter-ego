"use client";

import { useMemo } from "react";
import { useContentCalendar } from "@/modules/editorial";
import type { CalendarItem } from "@/modules/editorial";
import {
  conflictWindow,
  findScheduleConflicts,
  parseScheduleTime,
} from "./schedule-helpers";
import type { ScheduleDraft } from "./types";

/**
 * Calendar items within an hour of the chosen time, read from the content
 * calendar (the blog list has no schedule times); nothing is fetched until a
 * time is chosen.
 */
export function useScheduleConflicts(draft: ScheduleDraft): CalendarItem[] {
  const at = useMemo(() => parseScheduleTime(draft.time), [draft.time]);
  const window = useMemo(() => (at ? conflictWindow(at) : null), [at]);
  const { calendar } = useContentCalendar(
    window?.start,
    window?.end,
    window !== null,
  );
  return useMemo(
    () =>
      at && calendar
        ? findScheduleConflicts(calendar.items, { postId: draft.postId, at })
        : [],
    [at, calendar, draft.postId],
  );
}
