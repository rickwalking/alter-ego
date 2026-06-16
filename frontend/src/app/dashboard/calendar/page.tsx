"use client";

import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { CalendarSvgIcon } from "@/modules/editorial-operations";
import {
  CALENDAR_BTN_GHOST,
  CALENDAR_COLORS,
  CALENDAR_CONTENT_META,
  CALENDAR_FLEX_CENTER,
  CALENDAR_LEGEND,
  CALENDAR_MONO_FONT,
  CALENDAR_RESPONSIVE_STYLE,
  CALENDAR_STATUS_META,
  CALENDAR_VIEW_MODES,
  CALENDAR_WEEKDAY_HEADERS,
} from "@/modules/editorial-operations";
import {
  buildCalendarDaysFromApi,
  buildEmptyCalendarDays,
} from "@/modules/editorial-operations";
import type { CalendarContentType } from "@/modules/editorial-operations";
import { useContentCalendar } from "@/modules/editorial";
import {
  NEON_BORDER_FOCUS,
  NEON_BORDER_SUBTLE,
  NEON_RED,
} from "@/constants/neon";

const CONTENT_TYPE_ICON: Record<
  CalendarContentType,
  "grid" | "file" | "cal" | "user"
> = {
  carousel: "grid",
  blog: "file",
  meeting: "cal",
  management: "user",
};

export default function CalendarPage() {
  const { calendar, loading, error } = useContentCalendar();
  const days =
    calendar && calendar.items.length > 0
      ? buildCalendarDaysFromApi(calendar.items)
      : buildEmptyCalendarDays();

  return (
    <div
      style={{
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        color: CALENDAR_COLORS.txt,
        background: CALENDAR_COLORS.bg,
        minHeight: "100vh",
      }}
    >
      {error && (
        <p className="text-center py-4" style={{ color: NEON_RED }}>
          {error}
        </p>
      )}
      {loading && (
        <div className="flex justify-center py-12">
          <NeonSpinner size="lg" />
        </div>
      )}
      <div
        style={{
          height: 56,
          ...CALENDAR_FLEX_CENTER,
          justifyContent: "space-between",
          padding: "0 32px",
          borderBottom: `1px solid ${CALENDAR_COLORS.bdr}`,
          background: "rgba(6,10,18,0.6)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 50,
          opacity: loading ? 0.5 : 1,
        }}
      >
        <div style={{ ...CALENDAR_FLEX_CENTER, gap: 12 }}>
          <span
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: CALENDAR_COLORS.txt,
              letterSpacing: "-0.02em",
            }}
          >
            Calendar
          </span>
          <span
            style={{
              fontFamily: CALENDAR_MONO_FONT,
              fontSize: 11,
              color: CALENDAR_COLORS.tD,
            }}
          >
            /{" "}
            <span style={{ color: CALENDAR_COLORS.tM }}>content calendar</span>
          </span>
        </div>
        <div style={{ ...CALENDAR_FLEX_CENTER, gap: 16 }}>
          <button type="button" style={CALENDAR_BTN_GHOST}>
            <CalendarSvgIcon name="sync" size={14} /> Sync
          </button>
          <button
            type="button"
            style={{
              ...CALENDAR_BTN_GHOST,
              border: "none",
              background: `linear-gradient(135deg,${CALENDAR_COLORS.cyan} 0%,#0090b0 100%)`,
              color: CALENDAR_COLORS.bg,
              boxShadow: `0 0 16px ${CALENDAR_COLORS.cD}`,
            }}
          >
            <CalendarSvgIcon name="plus" size={14} /> Schedule Post
          </button>
        </div>
      </div>

      <div style={{ padding: "28px 32px" }}>
        <div
          style={{
            ...CALENDAR_FLEX_CENTER,
            justifyContent: "space-between",
            marginBottom: 20,
          }}
        >
          <div style={{ ...CALENDAR_FLEX_CENTER, gap: 12 }}>
            <button
              type="button"
              aria-label="Previous month"
              style={{
                ...CALENDAR_BTN_GHOST,
                padding: 8,
                lineHeight: 0,
                justifyContent: "center",
              }}
            >
              <CalendarSvgIcon name="left" />
            </button>
            <h2
              style={{
                fontSize: 20,
                fontWeight: 800,
                color: CALENDAR_COLORS.txt,
                letterSpacing: "-0.02em",
                margin: 0,
              }}
            >
              May 2026
            </h2>
            <button
              type="button"
              aria-label="Next month"
              style={{
                ...CALENDAR_BTN_GHOST,
                padding: 8,
                lineHeight: 0,
                justifyContent: "center",
              }}
            >
              <CalendarSvgIcon name="right" />
            </button>
            <button
              type="button"
              style={{ ...CALENDAR_BTN_GHOST, marginLeft: 8 }}
            >
              Today
            </button>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {CALENDAR_VIEW_MODES.map((viewMode) => (
              <button
                key={viewMode}
                type="button"
                style={{
                  ...CALENDAR_BTN_GHOST,
                  background:
                    viewMode === "Month" ? CALENDAR_COLORS.cD : "transparent",
                }}
              >
                {viewMode}
              </button>
            ))}
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(7,1fr)",
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
          {days.filter((day) => day.cur).length === 0 ? (
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
              <p
                style={{
                  fontSize: 12,
                  marginTop: 8,
                  color: CALENDAR_COLORS.tD,
                }}
              >
                Schedule a post or carousel to see it on the calendar.
              </p>
            </div>
          ) : (
            days.map((cell, index) => (
              <div
                key={`${cell.day}-${index}`}
                tabIndex={0}
                role="gridcell"
                style={{
                  minHeight: 100,
                  padding: 8,
                  background: cell.today
                    ? CALENDAR_COLORS.cD
                    : CALENDAR_COLORS.card,
                  border: cell.today
                    ? `1px solid ${NEON_BORDER_FOCUS}`
                    : "none",
                  cursor: "pointer",
                  opacity: cell.cur ? 1 : 0.3,
                }}
              >
                <div
                  style={{
                    fontFamily: CALENDAR_MONO_FONT,
                    fontSize: 13,
                    color: cell.today
                      ? CALENDAR_COLORS.cyan
                      : CALENDAR_COLORS.tM,
                    fontWeight: 600,
                    marginBottom: 6,
                  }}
                >
                  {cell.day}
                </div>
                {cell.events.map((event, eventIndex) => {
                  const contentMeta = CALENDAR_CONTENT_META[event.contentType];
                  return (
                    <div key={`${event.title}-${eventIndex}`}>
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
                        <CalendarSvgIcon
                          name={CONTENT_TYPE_ICON[event.contentType]}
                          size={9}
                        />{" "}
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
                      <div
                        style={{
                          fontSize: 8,
                          color: CALENDAR_COLORS.tM,
                          marginTop: 2,
                        }}
                      >
                        May {cell.day}
                      </div>
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <div
          style={{ display: "flex", gap: 16, marginTop: 16, flexWrap: "wrap" }}
        >
          {CALENDAR_LEGEND.map((item) => (
            <div
              key={item.l}
              style={{
                ...CALENDAR_FLEX_CENTER,
                gap: 6,
                fontSize: 11,
                color: CALENDAR_COLORS.tD,
                cursor: "pointer",
              }}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: item.c,
                  flexShrink: 0,
                }}
              />
              {item.l}
            </div>
          ))}
        </div>
      </div>

      <style>{CALENDAR_RESPONSIVE_STYLE}</style>
    </div>
  );
}
