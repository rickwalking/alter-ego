"use client";

import { parseISO } from "date-fns";
import { useLocale, useTranslations } from "next-intl";
import {
  CALENDAR_COLORS,
  CALENDAR_COLUMN_DATE_FORMAT,
  CALENDAR_DAY_TITLE_FORMAT,
  CALENDAR_MONO_FONT,
  CALENDAR_WEEKDAY_FORMAT,
} from "@/modules/editorial-operations";
import { toDateLocaleTag } from "@/lib/locale-format";
import { NEON_BORDER_FOCUS, NEON_BORDER_SUBTLE } from "@/constants/neon";
import { CalendarAgendaEvent } from "@/app/dashboard/calendar/calendar-agenda-event";
import type {
  CalendarWeekColumnProps,
  CalendarWeekViewProps,
} from "@/app/dashboard/calendar/types";

function CalendarWeekColumn({
  day,
  onOpenDay,
}: Readonly<CalendarWeekColumnProps>): React.ReactElement {
  const tag = toDateLocaleTag(useLocale());
  const t = useTranslations("workflow.calendar.agenda");
  const date = parseISO(day.iso);
  return (
    <li
      className="flex min-h-24 flex-col gap-2 p-2 md:min-h-64"
      style={{
        background: day.today ? CALENDAR_COLORS.cD : CALENDAR_COLORS.card,
        outline: day.today ? `1px solid ${NEON_BORDER_FOCUS}` : "none",
      }}
    >
      <button
        type="button"
        onClick={() => onOpenDay(date)}
        aria-current={day.today ? "date" : undefined}
        aria-label={t("openDay", {
          date: date.toLocaleDateString(tag, CALENDAR_DAY_TITLE_FORMAT),
        })}
        className="flex items-baseline gap-2 rounded text-left focus-visible:outline focus-visible:outline-2"
        style={{
          fontFamily: CALENDAR_MONO_FONT,
          color: day.today ? CALENDAR_COLORS.cyan : CALENDAR_COLORS.tM,
        }}
      >
        <span className="text-[10px] tracking-widest uppercase">
          {date.toLocaleDateString(tag, CALENDAR_WEEKDAY_FORMAT)}
        </span>
        <span className="text-sm font-semibold">
          {date.toLocaleDateString(tag, CALENDAR_COLUMN_DATE_FORMAT)}
        </span>
      </button>
      {day.events.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {day.events.map((event) => (
            <CalendarAgendaEvent key={event.id} event={event} />
          ))}
        </ul>
      )}
    </li>
  );
}

/**
 * Seven day columns from the week's first day; on narrow screens (375px) the
 * days stack as rows instead of crushing into seven columns. A day's header
 * opens it in the day view.
 */
export function CalendarWeekView({
  days,
  onOpenDay,
}: Readonly<CalendarWeekViewProps>): React.ReactElement {
  return (
    <ol
      className="grid grid-cols-1 overflow-hidden rounded-lg md:grid-cols-7"
      style={{
        gap: 1,
        background: CALENDAR_COLORS.cG,
        border: `1px solid ${NEON_BORDER_SUBTLE}`,
      }}
    >
      {days.map((day) => (
        <CalendarWeekColumn key={day.iso} day={day} onOpenDay={onOpenDay} />
      ))}
    </ol>
  );
}
