"use client";

import { format, parseISO } from "date-fns";
import { CalendarSvgIcon } from "@/modules/editorial-operations";
import {
  CALENDAR_COLORS,
  CALENDAR_CONTENT_META,
  CALENDAR_EVENT_DAY_FORMAT,
  CALENDAR_FLEX_CENTER,
  CALENDAR_MONO_FONT,
  CALENDAR_STATUS_META,
  CALENDAR_WEEKDAY_HEADERS,
} from "@/modules/editorial-operations";
import { NEON_BORDER_FOCUS, NEON_BORDER_SUBTLE } from "@/constants/neon";
import { CONTENT_TYPE_ICON } from "@/app/dashboard/calendar/constants";
import type {
  CalendarDayCellProps,
  CalendarDayEventProps,
  CalendarGridProps,
} from "@/app/dashboard/calendar/types";

function CalendarEmptyMonth(): React.ReactElement {
  return (
    <div
      style={{
        gridColumn: "1 / -1",
        padding: "60px 20px",
        textAlign: "center",
        color: CALENDAR_COLORS.tD,
      }}
    >
      <CalendarSvgIcon name="cal" size={48} />
      <p style={{ fontSize: 15, color: CALENDAR_COLORS.tM, margin: 0 }}>
        No scheduled content this month
      </p>
      <p style={{ fontSize: 12, marginTop: 8, color: CALENDAR_COLORS.tD }}>
        Schedule a post or carousel to see it on the calendar.
      </p>
    </div>
  );
}

function CalendarDayEvent({
  event,
  dateLabel,
}: CalendarDayEventProps): React.ReactElement {
  const contentMeta = CALENDAR_CONTENT_META[event.contentType];
  return (
    <div>
      <div
        tabIndex={0}
        role="button"
        style={{
          padding: "2px 6px",
          borderRadius: 3,
          fontSize: 10,
          marginBottom: 2,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          cursor: "pointer",
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
        {event.title}
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
        {contentMeta.l}
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
          {CALENDAR_STATUS_META[event.status].l}
        </div>
      )}
      <div style={{ fontSize: 8, color: CALENDAR_COLORS.tM, marginTop: 2 }}>
        {dateLabel}
      </div>
    </div>
  );
}

function CalendarDayCell({ cell }: CalendarDayCellProps): React.ReactElement {
  const dateLabel = format(parseISO(cell.iso), CALENDAR_EVENT_DAY_FORMAT);
  return (
    <div
      tabIndex={0}
      role="gridcell"
      className="snap-start"
      style={{
        minHeight: 100,
        padding: 8,
        background: cell.today ? CALENDAR_COLORS.cD : CALENDAR_COLORS.card,
        border: cell.today ? `1px solid ${NEON_BORDER_FOCUS}` : "none",
        cursor: "pointer",
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

export function CalendarGrid({ days }: CalendarGridProps): React.ReactElement {
  const hasCurrentDays = days.filter((day) => day.cur).length > 0;
  return (
    <div className="overflow-x-auto [overscroll-behavior-x:contain]">
      <div
        // Keep the month view; scroll-snap horizontally on small screens so
        // cells stay ≥~91px wide (min-w 640 / 7) instead of crushing.
        className="grid min-w-[640px] snap-x snap-mandatory grid-cols-7"
        style={{
          gap: 1,
          background: CALENDAR_COLORS.cG,
          borderRadius: 8,
          overflow: "hidden",
          border: `1px solid ${NEON_BORDER_SUBTLE}`,
        }}
      >
        {CALENDAR_WEEKDAY_HEADERS.map((header) => (
          <div
            key={header}
            className="snap-start"
            style={{
              padding: 10,
              textAlign: "center",
              fontFamily: CALENDAR_MONO_FONT,
              fontSize: 10,
              textTransform: "uppercase",
              letterSpacing: 2,
              color: CALENDAR_COLORS.tD,
              background: "rgba(6,10,18,0.5)",
              fontWeight: 700,
            }}
          >
            {header}
          </div>
        ))}
        {hasCurrentDays ? (
          days.map((cell) => <CalendarDayCell key={cell.iso} cell={cell} />)
        ) : (
          <CalendarEmptyMonth />
        )}
      </div>
    </div>
  );
}
