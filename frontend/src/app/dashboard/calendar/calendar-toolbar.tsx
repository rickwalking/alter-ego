"use client";

import { useTranslations } from "next-intl";
import { CalendarSvgIcon } from "@/modules/editorial-operations";
import {
  CALENDAR_BTN_GHOST,
  CALENDAR_COLORS,
  CALENDAR_VIEWS,
} from "@/modules/editorial-operations";
import type {
  CalendarToolbarProps,
  CalendarViewSwitchProps,
} from "@/app/dashboard/calendar/types";

/** Month / Week / Day toggle buttons; the active one is `aria-pressed`. */
function CalendarViewSwitch({
  view,
  onViewChange,
}: Readonly<CalendarViewSwitchProps>): React.ReactElement {
  const t = useTranslations("workflow.calendar.toolbar");
  return (
    <div
      role="group"
      aria-label={t("viewsLabel")}
      style={{ display: "flex", gap: 8 }}
    >
      {CALENDAR_VIEWS.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={option === view}
          onClick={() => onViewChange(option)}
          style={{
            ...CALENDAR_BTN_GHOST,
            background: option === view ? CALENDAR_COLORS.cD : "transparent",
          }}
        >
          {t(`views.${option}`)}
        </button>
      ))}
    </div>
  );
}

export function CalendarToolbar({
  title,
  view,
  onPrev,
  onNext,
  onToday,
  onViewChange,
}: Readonly<CalendarToolbarProps>): React.ReactElement {
  const t = useTranslations("workflow.calendar.toolbar");
  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          aria-label={t(`previous.${view}`)}
          onClick={onPrev}
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
          aria-live="polite"
          style={{
            fontSize: 20,
            fontWeight: 800,
            color: CALENDAR_COLORS.txt,
            letterSpacing: "-0.02em",
            margin: 0,
          }}
        >
          {title}
        </h2>
        <button
          type="button"
          aria-label={t(`next.${view}`)}
          onClick={onNext}
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
          onClick={onToday}
          style={{ ...CALENDAR_BTN_GHOST, marginLeft: 8 }}
        >
          {t("today")}
        </button>
      </div>
      <CalendarViewSwitch view={view} onViewChange={onViewChange} />
    </div>
  );
}
