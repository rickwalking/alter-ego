"use client";

import { useLocale, useTranslations } from "next-intl";
import {
  CALENDAR_COLORS,
  CALENDAR_CONTENT_META,
  CALENDAR_MONO_FONT,
  CALENDAR_STATUS_META,
  CalendarSvgIcon,
} from "@/modules/editorial-operations";
import { formatLocaleTime } from "@/lib/locale-format";
import { CONTENT_TYPE_ICON } from "@/app/dashboard/calendar/constants";
import type { CalendarAgendaEventProps } from "@/app/dashboard/calendar/types";

/**
 * One item in the week and day views: its local time (or "All day" for a
 * date-only item), title ("Untitled" when the item has none), content type
 * and workflow status, with the month grid's labels.
 */
export function CalendarAgendaEvent({
  event,
}: Readonly<CalendarAgendaEventProps>): React.ReactElement {
  const locale = useLocale();
  const t = useTranslations("workflow.calendar");
  const contentMeta = CALENDAR_CONTENT_META[event.contentType];
  return (
    <li
      className="flex flex-col gap-1 rounded px-2 py-1.5"
      style={{
        background: contentMeta.d,
        borderLeft: `2px solid ${contentMeta.c}`,
      }}
    >
      <span
        className="text-[10px]"
        style={{ fontFamily: CALENDAR_MONO_FONT, color: CALENDAR_COLORS.tM }}
      >
        {event.at ? formatLocaleTime(event.at, locale) : t("agenda.allDay")}
      </span>
      <span className="text-xs break-words" style={{ color: contentMeta.c }}>
        {event.title || t("untitled")}
      </span>
      <span
        className="flex flex-wrap items-center gap-1.5 text-[10px]"
        style={{ fontFamily: CALENDAR_MONO_FONT, color: CALENDAR_COLORS.tD }}
      >
        <CalendarSvgIcon name={CONTENT_TYPE_ICON[event.contentType]} size={9} />
        {t(`contentType.${event.contentType}`)}
        {event.status && (
          <span
            className="rounded px-1.5"
            style={{
              background: CALENDAR_STATUS_META[event.status].b,
              color: CALENDAR_STATUS_META[event.status].c,
            }}
          >
            {t(`status.${event.status}`)}
          </span>
        )}
      </span>
    </li>
  );
}
