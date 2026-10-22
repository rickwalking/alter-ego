"use client";

import { useLocale, useTranslations } from "next-intl";
import { CalendarSvgIcon } from "@/modules/editorial-operations";
import {
  CALENDAR_COLORS,
  CALENDAR_CONTENT_META,
  CALENDAR_FLEX_CENTER,
  CALENDAR_MONO_FONT,
  CALENDAR_STATUS_META,
  formatCalendarDayLabel,
} from "@/modules/editorial-operations";
import { NEON_BORDER_FOCUS } from "@/constants/neon";
import { CONTENT_TYPE_ICON } from "@/app/dashboard/calendar/constants";
import type {
  CalendarDayCellProps,
  CalendarDayEventProps,
} from "@/app/dashboard/calendar/types";

function CalendarDayEvent({
  event,
  dateLabel,
}: Readonly<CalendarDayEventProps>): React.ReactElement {
  const t = useTranslations("workflow.calendar");
  const contentMeta = CALENDAR_CONTENT_META[event.contentType];
  const title = event.title || t("untitled");
  return (
    <div>
      <div
        title={title}
        style={{
          padding: "2px 6px",
          borderRadius: 3,
          fontSize: 10,
          marginBottom: 2,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          background:
            event.contentType === "meeting"
              ? CALENDAR_COLORS.aD
              : contentMeta.d,
          color:
            event.contentType === "meeting"
              ? CALENDAR_COLORS.amber
              : contentMeta.c,
        }}
      >
        {title}
      </div>
      <div
        style={{
          ...CALENDAR_FLEX_CENTER,
          gap: 4,
          marginBottom: 4,
          fontSize: 9,
          fontFamily: CALENDAR_MONO_FONT,
          color: CALENDAR_COLORS.tD,
        }}
      >
        <CalendarSvgIcon name={CONTENT_TYPE_ICON[event.contentType]} size={9} />{" "}
        {t(`contentType.${event.contentType}`)}
      </div>
      {event.status && (
        <div
          style={{
            fontSize: 9,
            padding: "1px 6px",
            borderRadius: 3,
            fontFamily: CALENDAR_MONO_FONT,
            background: CALENDAR_STATUS_META[event.status].b,
            color: CALENDAR_STATUS_META[event.status].c,
            display: "inline-block",
          }}
        >
          {t(`status.${event.status}`)}
        </div>
      )}
      <div style={{ fontSize: 8, color: CALENDAR_COLORS.tM, marginTop: 2 }}>
        {dateLabel}
      </div>
    </div>
  );
}

/** One day of the month grid: its number and its event chips. */
export function CalendarDayCell({
  cell,
}: Readonly<CalendarDayCellProps>): React.ReactElement {
  const locale = useLocale();
  const dateLabel = formatCalendarDayLabel(cell.iso, locale);
  return (
    <div
      role="cell"
      className="snap-start"
      style={{
        minHeight: 100,
        padding: 8,
        background: cell.today ? CALENDAR_COLORS.cD : CALENDAR_COLORS.card,
        border: cell.today ? `1px solid ${NEON_BORDER_FOCUS}` : "none",
        opacity: cell.cur ? 1 : 0.3,
      }}
    >
      <div
        style={{
          fontFamily: CALENDAR_MONO_FONT,
          fontSize: 13,
          color: cell.today ? CALENDAR_COLORS.cyan : CALENDAR_COLORS.tM,
          fontWeight: 600,
          marginBottom: 6,
        }}
      >
        {cell.day}
      </div>
      {cell.events.map((event, eventIndex) => (
        <CalendarDayEvent
          key={`${event.title}-${eventIndex}`}
          event={event}
          dateLabel={dateLabel}
        />
      ))}
    </div>
  );
}
